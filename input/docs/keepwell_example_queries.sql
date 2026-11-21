-- =====================================================================
-- Keepwell example queries v0.2  (run after keepwell_schema.sql v0.2)
-- Named parameters are written :name; bind them from the app.
-- Run as role kw_app with  SET kw.centre_id = '<centre uuid>'  for centre work,
-- or  SET kw.role = 'platform'  for platform jobs. Geography queries need PostGIS,
-- Q19 needs pgvector. Q12 and Q13 read a visit_plan, and Q18 reads access_log; the
-- app writes both, so they return rows only after the app has run (Q18 after Q17).
-- =====================================================================
SET search_path = kw, public;

-- =====================================================================
-- A. Arrival: who is this, can this centre act, can it serve them
-- =====================================================================

-- ---------------------------------------------------------------------
-- Q1. Identify the household behind a call or message.
--     Looks up the keyed phone hash among household and member numbers
--     (external_ref), and says whether this centre already knows them.
--     :phone_hash (bytea, keyed hash of the normalised number)  :centre_id
-- ---------------------------------------------------------------------
SELECT x.entity_id                                          AS household_id,
       h.verified_via,
       EXISTS (SELECT 1 FROM household_centre_link l
               WHERE l.household_id = h.id AND l.centre_id = :centre_id) AS known_to_this_centre,
       (SELECT count(*) FROM household_centre_link l
        WHERE l.household_id = h.id AND l.centre_id <> :centre_id)       AS other_centres,
       (SELECT count(*) FROM appliance a WHERE a.household_id = h.id AND a.status = 'active') AS appliances
FROM external_ref x
JOIN household h ON h.id = x.entity_id AND h.status = 'active'
WHERE x.entity_type = 'household'
  AND x.ref_type    = 'phone'
  AND x.ref_norm    = encode(:phone_hash, 'hex');

-- ---------------------------------------------------------------------
-- Q2. Identify an appliance from a serial read off a sticker or invoice.
--     Brand plus normalised serial is the global key; a hit on another
--     household's appliance is a conflict for the agent to resolve, not a merge.
--     :brand_id  :serial_norm
-- ---------------------------------------------------------------------
SELECT a.id AS appliance_id, a.household_id, a.model_id, a.identity_status, a.purchase_date
FROM appliance a
WHERE a.brand_id = :brand_id AND a.serial_norm = :serial_norm;

-- ---------------------------------------------------------------------
-- Q3. Authority check: may the receiving centre honour this ticket's
--     entitlement for this brand today? Warranty work needs
--     'authorised_service'. Anything else is paid work, or goes back to
--     the brand with the reason. There is no search for another centre.
--     :ticket_id
-- ---------------------------------------------------------------------
SELECT t.id AS ticket_id, b.name AS brand, t.entitlement,
       centre_authority(t.centre_id, ap.brand_id, current_date) AS authority,
       CASE
         WHEN t.job_type = 'installation' THEN
              CASE WHEN centre_authority(t.centre_id, ap.brand_id) IN ('authorised_service','installation_only')
                   THEN 'can_install' ELSE 'cannot_install' END
         WHEN t.entitlement IN ('brand_warranty','extended_warranty')
              AND centre_authority(t.centre_id, ap.brand_id) <> 'authorised_service'
              THEN 'return_to_brand_with_reason'
         WHEN centre_authority(t.centre_id, ap.brand_id) = 'installation_only' THEN 'cannot_repair'
         ELSE 'proceed'
       END AS decision
FROM ticket t
JOIN appliance ap ON ap.id = t.appliance_id
JOIN brand b      ON b.id  = ap.brand_id
WHERE t.id = :ticket_id;

-- ---------------------------------------------------------------------
-- Q4. Service area and capacity at the receiving centre.
--     An address outside the centre's pincodes is told so politely; the
--     household is not sent to another centre by Keepwell.
--     :centre_id  :household_id  :category_code  :job_type
-- ---------------------------------------------------------------------
SELECT h.pincode,
       h.pincode = ANY (c.service_pincodes)                  AS in_service_area,
       :category_code = ANY (c.categories)                    AS category_served,
       coalesce(cc.daily_slots, 0)                            AS daily_slots,
       coalesce(cc.urgent_holdback, 0)                        AS urgent_holdback
FROM service_centre c
JOIN household h ON h.id = :household_id
LEFT JOIN centre_capacity cc ON cc.centre_id = c.id AND cc.category_code = :category_code AND cc.job_type = :job_type
WHERE c.id = :centre_id;

-- =====================================================================
-- B. Urgency, consent gates and the self-fix
-- =====================================================================

-- ---------------------------------------------------------------------
-- Q5. The urgency queue for a centre: open tickets by class, then the
--     time the household needs the visit by, with the agent's reason.
--     :centre_id
-- ---------------------------------------------------------------------
SELECT t.id AS ticket_id, t.urgency_class, t.needed_by, t.status, t.trigger,
       ua.rule_codes, ua.reason, ua.assessed_by, ua.protective_steps_sent
FROM ticket t
LEFT JOIN LATERAL (SELECT * FROM urgency_assessment u WHERE u.ticket_id = t.id ORDER BY u.created_at DESC LIMIT 1) ua ON true
WHERE t.centre_id = :centre_id
  AND t.status NOT IN ('closed','cancelled','completed')
ORDER BY CASE t.urgency_class WHEN 'safety' THEN 1 WHEN 'urgent' THEN 2 WHEN 'standard' THEN 3 ELSE 4 END,
         t.needed_by NULLS LAST, t.created_at;

-- ---------------------------------------------------------------------
-- Q6. Consent gate funnel, per centre. Gate 1 asks "okay to try a safe
--     fix?"; gate 2 (only after yes) asks "switch to video or carry on here?".
-- ---------------------------------------------------------------------
SELECT g.centre_id, g.gate,
       count(*)                                         AS rows,
       count(*) FILTER (WHERE g.answer = 'yes')         AS yes,
       count(*) FILTER (WHERE g.answer = 'no')          AS no,
       count(*) FILTER (WHERE g.answer = 'silence')     AS silence,
       count(*) FILTER (WHERE g.answer = 'not_asked')   AS not_asked,
       count(*) FILTER (WHERE g.choice = 'switch_to_video') AS chose_video,
       count(*) FILTER (WHERE g.not_asked_reason = 'safety_flag') AS skipped_for_safety
FROM consent_gate g
GROUP BY g.centre_id, g.gate
ORDER BY g.centre_id, g.gate;

-- ---------------------------------------------------------------------
-- Q7. Safe fixes the agent may offer for this appliance and symptom.
--     Only active entries pass, and the CHECKs on the catalogue already
--     guarantee: at most 6 steps, at most 12 minutes, reversible, no
--     tools, a named reviewer and a manual page. Brand and series
--     specific entries rank above generic ones.
--     :category_code  :brand_id  :model_series  :symptom (a word from the household's description)
-- ---------------------------------------------------------------------
SELECT f.code, f.title, f.step_count, f.est_minutes, f.opens_panel, f.worst_case, f.manual_page,
       e.attempts, e.worked_rate
FROM safe_fix_catalogue f
LEFT JOIN safe_fix_effectiveness e ON e.code = f.code
WHERE f.status = 'active'
  AND f.category_code = :category_code
  AND (f.brand_id IS NULL OR f.brand_id = :brand_id)
  AND (f.model_series IS NULL OR f.model_series = :model_series)
  AND :symptom = ANY (f.symptom_terms)
ORDER BY (f.brand_id IS NOT NULL) DESC, (f.model_series IS NOT NULL) DESC, e.worked_rate DESC NULLS LAST;

-- ---------------------------------------------------------------------
-- Q8. What was tried on a ticket, in order. This is what the agent reads
--     when a fix fails and it re-runs the process, and what the visit
--     plan and the technician brief carry as "already tried".
--     :ticket_id
-- ---------------------------------------------------------------------
SELECT tried FROM tried_summary WHERE ticket_id = :ticket_id;

-- ---------------------------------------------------------------------
-- Q9. Safe-fix catalogue health: how often each fix works, and which
--     entries are past review or retired.
-- ---------------------------------------------------------------------
SELECT f.code, f.status, f.reviewed_on, f.review_due,
       (f.review_due < current_date)                    AS overdue,
       coalesce(e.attempts, 0)                          AS attempts,
       coalesce(e.worked, 0)                            AS worked,
       coalesce(e.safety_stops, 0)                      AS safety_stops,
       e.worked_rate
FROM safe_fix_catalogue f
LEFT JOIN safe_fix_effectiveness e ON e.code = f.code
ORDER BY f.status, e.attempts DESC NULLS LAST;

-- ---------------------------------------------------------------------
-- Q10. Resolution mix by trigger: how many tickets the self-fix closed
--      without a visit, and how many needed one.
-- ---------------------------------------------------------------------
SELECT t.trigger, t.resolution, count(*) AS tickets
FROM ticket t
WHERE t.status IN ('closed','completed')
GROUP BY t.trigger, t.resolution
ORDER BY t.trigger, tickets DESC;

-- ---------------------------------------------------------------------
-- Q11. Where the centre overrode the agent. Each row is a training
--      signal: a reclassified urgency or a technician the centre picked
--      instead of the agent's first choice.
--      :centre_id
-- ---------------------------------------------------------------------
SELECT 'urgency' AS kind, u.ticket_id, u.created_at, u.class AS agent_or_console_value, u.reason
FROM urgency_assessment u
WHERE u.centre_id = :centre_id AND u.assessed_by = 'centre_console'
UNION ALL
SELECT 'assignment', a.ticket_id, a.created_at, a.technician_id::text, a.override_reason
FROM assignment_candidate a
WHERE a.centre_id = :centre_id AND a.chosen_by = 'centre_console'
ORDER BY created_at DESC;

-- =====================================================================
-- C. Technician, parts and slots, all inside the receiving centre
-- =====================================================================

-- ---------------------------------------------------------------------
-- Q12. Technician candidates inside the centre: hard filters only. The
--      score (fix confidence 30, parts readiness 25, time to visit 20,
--      route cost 15, reliability 5, household fit 5) is computed over
--      these rows from scoring_config; price is not scored.
--      :ticket_id  :plan_id  :slot_start  :slot_end  :max_km
-- ---------------------------------------------------------------------
SELECT te.id AS technician_id, te.name,
       round((ST_Distance(te.route_anchor, t.visit_location) / 1000)::numeric, 1) AS anchor_km,
       m.first_time_fix_rate, m.on_time_rate, te.languages
FROM ticket t
JOIN appliance ap  ON ap.id = t.appliance_id
JOIN visit_plan vp ON vp.id = :plan_id
JOIN technician te ON te.centre_id = t.centre_id AND te.active AND te.identity_verified
LEFT JOIN technician_metrics m
     ON m.technician_id = te.id AND m.category_code = 'ALL'
    AND m.period_end = (SELECT max(period_end) FROM technician_metrics WHERE technician_id = te.id)
WHERE t.id = :ticket_id
  AND EXISTS (SELECT 1 FROM technician_skill s
              WHERE s.technician_id = te.id
                AND s.category_code = ap.category_code
                AND (s.brand_id = ap.brand_id OR s.brand_id IS NULL)
                AND s.level >= 3)
  AND te.safety_certs @> vp.requires_safety_cert
  AND ST_DWithin(te.route_anchor, t.visit_location, :max_km * 1000)
  AND EXISTS (SELECT 1 FROM technician_availability av
              WHERE av.technician_id = te.id AND av.status = 'open'
                AND av.slot_start <= :slot_start AND av.slot_end >= :slot_end)
ORDER BY anchor_km;

-- ---------------------------------------------------------------------
-- Q13. Parts readiness: for each part in the plan, where it is
--      available, in ladder order (van, centre, parts centre).
--      :plan_id  :technician_id  :centre_id
-- ---------------------------------------------------------------------
SELECT pp.part_id, pc.part_no, pp.probability,
       src.holder_type, src.holder_id, src.quantity, src.as_of, src.confidence,
       CASE src.holder_type WHEN 'van' THEN 1 WHEN 'centre' THEN 2 ELSE 3 END AS ladder_rank
FROM plan_part pp
JOIN part_catalogue pc ON pc.id = pp.part_id
LEFT JOIN LATERAL (
  SELECT s.*
  FROM stock s
  WHERE s.part_id = pp.part_id AND s.quantity >= pp.quantity
    AND (   (s.holder_type = 'van'          AND s.holder_id = :technician_id)
         OR (s.holder_type = 'centre'       AND s.holder_id = :centre_id)
         OR (s.holder_type = 'parts_centre'))
  ORDER BY CASE s.holder_type WHEN 'van' THEN 1 WHEN 'centre' THEN 2 ELSE 3 END, s.confidence DESC
  LIMIT 1
) src ON true
WHERE pp.visit_plan_id = :plan_id
ORDER BY pp.probability DESC;

-- ---------------------------------------------------------------------
-- Q14. Parts centres near the technician's route anchor (not the
--      household), stocking a compatible part, by fill rate then distance.
--      :part_id  :technician_id  :radius_km
-- ---------------------------------------------------------------------
SELECT p.id AS parts_centre_id, p.name,
       round((ST_Distance(p.location, te.route_anchor) / 1000)::numeric, 1) AS km_from_anchor,
       p.fill_rate, s.quantity, s.confidence
FROM technician te
JOIN parts_centre p ON p.active AND ST_DWithin(p.location, te.route_anchor, :radius_km * 1000)
JOIN stock s ON s.holder_type = 'parts_centre' AND s.holder_id = p.id AND s.part_id = :part_id AND s.quantity > 0
WHERE te.id = :technician_id
ORDER BY p.fill_rate DESC NULLS LAST, km_from_anchor;

-- ---------------------------------------------------------------------
-- Q15. Batching: the technician's other visits that day near a new
--      ticket's address.
--      :technician_id  :ticket_id  :day  :radius_km
-- ---------------------------------------------------------------------
SELECT v.id AS visit_id, v.planned_start, v.planned_end,
       round((ST_Distance(t2.visit_location, t1.visit_location) / 1000)::numeric, 2) AS km_apart
FROM ticket t1
JOIN visit v   ON v.technician_id = :technician_id
              AND v.planned_start >= :day::date AND v.planned_start < :day::date + 1
JOIN ticket t2 ON t2.id = v.ticket_id
WHERE t1.id = :ticket_id
  AND ST_DWithin(t2.visit_location, t1.visit_location, :radius_km * 1000)
ORDER BY v.planned_start;

-- ---------------------------------------------------------------------
-- Q16. First-time fix rate per technician over the 90 days to a date.
--      :as_of (date)  :min_jobs (10 in production; lower on small data)
-- ---------------------------------------------------------------------
SELECT f.technician_id, f.category_code,
       count(*)                                         AS jobs,
       round(avg(f.fixed_first_time::int)::numeric, 3)  AS first_time_fix_rate
FROM first_visit_outcome f
WHERE f.planned_start >= :as_of::date - 90 AND f.planned_start < :as_of::date + 1
GROUP BY f.technician_id, f.category_code
HAVING count(*) >= :min_jobs
ORDER BY first_time_fix_rate DESC;

-- =====================================================================
-- D. Memory, sharing and privacy
-- =====================================================================

-- ---------------------------------------------------------------------
-- Q17. Technical history of an appliance for a centre that did not
--      record all of it. The function returns the centre's own rows
--      always, and other centres' technical rows only when the household
--      has consented; every such read lands in access_log. Prices and
--      notes never cross.
--      :appliance_id  :centre_id  :ticket_id
-- ---------------------------------------------------------------------
SELECT e.occurred_at, e.event_type, e.centre_id, e.details
FROM read_shared_history(:appliance_id, :centre_id, :ticket_id, 'repeat or related fault') e;

-- ---------------------------------------------------------------------
-- Q18. What the household can be shown about who looked at their
--      records: cross-centre reads for one household.
--      :household_id
-- ---------------------------------------------------------------------
SELECT l.occurred_at, l.actor_type, l.actor_centre_id, l.owner_centre_id, l.record_table, l.reason
FROM access_log l
WHERE l.cross_centre
  AND ((l.record_table = 'household' AND l.record_id = :household_id)
    OR (l.record_table = 'appliance_event'
        AND l.record_id IN (SELECT e.id FROM appliance_event e JOIN appliance a ON a.id = e.appliance_id WHERE a.household_id = :household_id)))
ORDER BY l.occurred_at DESC;

-- ---------------------------------------------------------------------
-- Q19. Semantic search over experience cases (pgvector, cosine
--      distance), filtered by brand and category before ranking.
--      :query_embedding is a 768-number vector built from the symptom text.
-- ---------------------------------------------------------------------
SELECT e.id, e.symptom_text, e.error_code, e.root_cause, e.parts, e.duration_min,
       1 - (e.embedding <=> :query_embedding) AS similarity
FROM experience_case e
WHERE e.brand_id = :brand_id
  AND e.category_code = :category_code
  AND e.verified_by_technician
ORDER BY e.embedding <=> :query_embedding
LIMIT 5;

-- ---------------------------------------------------------------------
-- Q20. Reminders to send today. The sender is the centre that last
--      served the appliance, the consent must be in force for that
--      centre (or platform-wide), and the household's monthly cap on
--      non-urgent reminders must not be reached.
--      :monthly_cap (platform setting, 2 by default)
-- ---------------------------------------------------------------------
SELECT r.id AS reminder_id, r.centre_id, r.household_id, r.appliance_id, r.reminder_type, r.template_name
FROM reminder r
JOIN household h ON h.id = r.household_id AND h.status = 'active'
JOIN appliance a ON a.id = r.appliance_id AND a.last_served_centre_id = r.centre_id
WHERE r.status = 'scheduled'
  AND r.due_on <= current_date
  AND EXISTS (SELECT 1 FROM current_consent c
              WHERE c.subject_type = 'household' AND c.subject_id = h.id
                AND (c.scope_centre_id IS NULL OR c.scope_centre_id = r.centre_id)
                AND c.purpose = CASE r.reminder_type
                                  WHEN 'warranty_ending' THEN 'warranty_alerts'
                                  WHEN 'rating_request'  THEN 'follow_up'
                                  WHEN 'after_repair'    THEN 'follow_up'
                                  ELSE 'service_reminders' END)
  AND (SELECT count(*) FROM reminder x
       WHERE x.household_id = h.id AND x.status IN ('sent','delivered','read','acted')
         AND x.sent_at >= date_trunc('month', now()))
      < :monthly_cap;

-- ---------------------------------------------------------------------
-- Q21. Appliance timeline for the household memory screen. Events the
--      centre recorded plus platform events; other centres' events come
--      only through Q17.
--      :appliance_id  :centre_id
-- ---------------------------------------------------------------------
SELECT e.occurred_at, e.event_type, e.details, e.ticket_id
FROM appliance_event e
WHERE e.appliance_id = :appliance_id
  AND (e.centre_id = :centre_id OR e.centre_id IS NULL)
ORDER BY e.occurred_at DESC
LIMIT 50;

-- =====================================================================
-- E. Visit and closure
-- =====================================================================

-- ---------------------------------------------------------------------
-- Q22. What a technician may see for a visit: address and phone only
--      after the slot is confirmed, and every read is logged.
--      :visit_id  :technician_id
-- ---------------------------------------------------------------------
WITH v AS (
  SELECT v.id, v.ticket_id, v.centre_id, t.household_id, t.visit_address
  FROM visit v
  JOIN ticket t ON t.id = v.ticket_id
  WHERE v.id = :visit_id
    AND v.technician_id = :technician_id
    AND t.status IN ('booked','scheduled','in_progress','needs_part')
), logged AS (
  INSERT INTO access_log (actor_type, actor_id, actor_centre_id, record_table, record_id, ticket_id, reason)
  SELECT 'technician', :technician_id::text, v.centre_id, 'household', v.household_id, v.ticket_id, 'visit_contact'
  FROM v
  RETURNING 1
)
SELECT v.visit_address, h.phone_enc
FROM v JOIN household h ON h.id = v.household_id;

-- ---------------------------------------------------------------------
-- Q23. Close a visit job. Allowed only when the household's OTP has
--      been verified; the code itself is never stored, only the
--      provider's reference. Self-fix tickets close the same way on the
--      ticket row (Q24).
--      :visit_id  :otp_ref
-- ---------------------------------------------------------------------
UPDATE visit
SET closure_otp_ref = :otp_ref,
    closure_confirmed_at = now(),
    check_out_at = COALESCE(check_out_at, now())
WHERE id = :visit_id
  AND outcome IS NOT NULL
  AND closure_confirmed_at IS NULL;

-- ---------------------------------------------------------------------
-- Q24. Close a self-fix ticket after the household confirms by OTP.
--      :ticket_id  :otp_ref
-- ---------------------------------------------------------------------
UPDATE ticket
SET closure_otp_ref = :otp_ref,
    closure_confirmed_at = now(),
    closed_at = now(),
    status = 'closed',
    resolution = 'self_fix'
WHERE id = :ticket_id
  AND status = 'self_fix'
  AND EXISTS (SELECT 1 FROM fix_attempt f WHERE f.ticket_id = ticket.id AND f.outcome = 'worked');
