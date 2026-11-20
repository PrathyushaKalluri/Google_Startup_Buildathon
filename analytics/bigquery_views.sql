-- ============================================================================
-- Keepwell Analytics: BigQuery Standard SQL Views
-- Dataset: keepwell_analytics (Region: asia-south1 / Mumbai)
-- Privacy: Pseudonymous IDs only (no raw phones, addresses, or PII).
-- Source tables are exported from Cloud SQL (schema kw) into keepwell_analytics.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. First-Time Fix (FTF)
--    Contract C11: first visit ended 'fixed' and ticket had no other visit.
--    Repair jobs only. Mirrors Postgres view kw.first_visit_outcome.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW `keepwell_analytics.v_first_time_fix` AS
WITH ranked_visits AS (
  SELECT
    v.id AS visit_id,
    v.ticket_id,
    v.centre_id,
    v.technician_id,
    v.planned_start,
    v.outcome,
    ROW_NUMBER() OVER (PARTITION BY v.ticket_id ORDER BY v.planned_start) AS visit_rn,
    COUNT(*) OVER (PARTITION BY v.ticket_id) AS visits_on_ticket
  FROM `keepwell_analytics.visit` v
),
first_visit AS (
  SELECT
    rv.ticket_id,
    rv.visit_id,
    rv.centre_id,
    rv.technician_id,
    a.brand_id,
    a.category_code,
    DATE_TRUNC(DATE(rv.planned_start, 'Asia/Kolkata'), MONTH) AS visit_month,
    DATE(rv.planned_start, 'Asia/Kolkata') AS visit_date,
    (rv.outcome = 'fixed' AND rv.visits_on_ticket = 1) AS fixed_first_time
  FROM ranked_visits rv
  JOIN `keepwell_analytics.ticket` t ON t.id = rv.ticket_id
  JOIN `keepwell_analytics.appliance` a ON a.id = t.appliance_id
  WHERE rv.visit_rn = 1
    AND rv.outcome IS NOT NULL
    AND t.job_type = 'repair'
)
SELECT
  centre_id,
  brand_id,
  category_code,
  technician_id,
  visit_month,
  visit_date,
  COUNT(*) AS repair_first_visits,
  COUNTIF(fixed_first_time) AS fixed_first_time_count,
  SAFE_DIVIDE(COUNTIF(fixed_first_time), COUNT(*)) AS ftf_rate
FROM first_visit
GROUP BY centre_id, brand_id, category_code, technician_id, visit_month, visit_date;

-- ----------------------------------------------------------------------------
-- 2. FVR-14 (First-Visit Resolution, 14 days)
--    Contract C11: repair ticket whose first visit ended 'fixed', was closed
--    by OTP (closure_confirmed_at IS NOT NULL), and has no new repair ticket
--    for the same appliance and same fault family within 14 days of closure.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW `keepwell_analytics.v_fvr_14d` AS
WITH ticket_fault AS (
  SELECT
    t.id AS ticket_id,
    t.centre_id,
    t.appliance_id,
    a.brand_id,
    a.category_code,
    a.model_id,
    t.job_type,
    t.closure_confirmed_at,
    t.closed_at,
    t.created_at,
    COALESCE(
      JSON_VALUE(t.case_card, '$.fault_family'),
      (
        SELECT ph.cause
        FROM `keepwell_analytics.visit_plan` vp
        JOIN `keepwell_analytics.plan_hypothesis` ph ON ph.visit_plan_id = vp.id AND ph.rank = 1
        WHERE vp.ticket_id = t.id
        ORDER BY vp.version DESC
        LIMIT 1
      ),
      'unknown'
    ) AS fault_family
  FROM `keepwell_analytics.ticket` t
  JOIN `keepwell_analytics.appliance` a ON a.id = t.appliance_id
  WHERE t.job_type = 'repair'
),
first_visit AS (
  SELECT
    v.ticket_id,
    v.outcome,
    v.closure_confirmed_at AS visit_closure_confirmed_at,
    ROW_NUMBER() OVER (PARTITION BY v.ticket_id ORDER BY v.planned_start) AS visit_rn
  FROM `keepwell_analytics.visit` v
),
eligible AS (
  SELECT
    tf.ticket_id,
    tf.centre_id,
    tf.appliance_id,
    tf.brand_id,
    tf.category_code,
    tf.model_id,
    tf.fault_family,
    COALESCE(tf.closure_confirmed_at, fv.visit_closure_confirmed_at) AS otp_closed_at,
    fv.outcome AS first_visit_outcome,
    EXISTS (
      SELECT 1
      FROM ticket_fault tf2
      WHERE tf2.appliance_id = tf.appliance_id
        AND tf2.ticket_id != tf.ticket_id
        AND tf2.fault_family = tf.fault_family
        AND tf2.created_at > COALESCE(tf.closure_confirmed_at, fv.visit_closure_confirmed_at)
        AND tf2.created_at <= TIMESTAMP_ADD(
          COALESCE(tf.closure_confirmed_at, fv.visit_closure_confirmed_at),
          INTERVAL 14 DAY
        )
    ) AS has_repeat_within_14d
  FROM ticket_fault tf
  JOIN first_visit fv ON fv.ticket_id = tf.ticket_id AND fv.visit_rn = 1
  WHERE fv.outcome IS NOT NULL
)
SELECT
  centre_id,
  brand_id,
  category_code,
  DATE_TRUNC(DATE(otp_closed_at, 'Asia/Kolkata'), MONTH) AS closure_month,
  COUNT(*) AS evaluated_repair_tickets,
  COUNTIF(
    first_visit_outcome = 'fixed'
    AND otp_closed_at IS NOT NULL
    AND NOT has_repeat_within_14d
  ) AS fvr_14d_passed_count,
  COUNTIF(has_repeat_within_14d) AS repeat_14d_count,
  SAFE_DIVIDE(
    COUNTIF(
      first_visit_outcome = 'fixed'
      AND otp_closed_at IS NOT NULL
      AND NOT has_repeat_within_14d
    ),
    COUNT(*)
  ) AS fvr_14d_rate
FROM eligible
WHERE otp_closed_at IS NOT NULL
GROUP BY centre_id, brand_id, category_code, closure_month;

-- ----------------------------------------------------------------------------
-- 3. Self-Fix Resolution Rate & Minutes Saved
--    Contract C11: share of repair tickets where a catalogue self-fix ended
--    'worked' and no visit was needed. Estimates saved technician minutes
--    (baseline 60 min visit minus self-fix est_minutes).
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW `keepwell_analytics.v_self_fix_resolution` AS
WITH ticket_visits AS (
  SELECT ticket_id, COUNT(*) AS visit_count
  FROM `keepwell_analytics.visit`
  GROUP BY ticket_id
),
worked_fix AS (
  SELECT
    fa.ticket_id,
    MIN(sfc.est_minutes) AS fix_minutes,
    ANY_VALUE(sfc.code) AS fix_code
  FROM `keepwell_analytics.fix_attempt` fa
  JOIN `keepwell_analytics.safe_fix_catalogue` sfc ON sfc.id = fa.catalogue_id
  WHERE fa.outcome = 'worked'
  GROUP BY fa.ticket_id
)
SELECT
  t.centre_id,
  a.brand_id,
  a.category_code,
  DATE_TRUNC(DATE(t.created_at, 'Asia/Kolkata'), MONTH) AS ticket_month,
  COUNT(*) AS total_repair_tickets,
  COUNTIF(wf.ticket_id IS NOT NULL AND COALESCE(tv.visit_count, 0) = 0) AS self_fix_resolved_count,
  SAFE_DIVIDE(
    COUNTIF(wf.ticket_id IS NOT NULL AND COALESCE(tv.visit_count, 0) = 0),
    COUNT(*)
  ) AS self_fix_resolution_rate,
  SUM(
    IF(
      wf.ticket_id IS NOT NULL AND COALESCE(tv.visit_count, 0) = 0,
      GREATEST(60 - COALESCE(wf.fix_minutes, 10), 0),
      0
    )
  ) AS est_minutes_saved
FROM `keepwell_analytics.ticket` t
LEFT JOIN `keepwell_analytics.appliance` a ON a.id = t.appliance_id
LEFT JOIN ticket_visits tv ON tv.ticket_id = t.id
LEFT JOIN worked_fix wf ON wf.ticket_id = t.id
WHERE t.job_type = 'repair'
GROUP BY t.centre_id, a.brand_id, a.category_code, ticket_month;

-- ----------------------------------------------------------------------------
-- 4. Consent Gate Funnel
--    Contract C11: repair tickets where Gate 1 was asked -> yes ->
--    Gate 2 asked -> switch_to_video (plus safety/job_type skip tracking).
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW `keepwell_analytics.v_gate_funnel` AS
WITH gates_pivoted AS (
  SELECT
    g.centre_id,
    g.ticket_id,
    DATE_TRUNC(DATE(MIN(g.asked_at), 'Asia/Kolkata'), MONTH) AS gate_month,
    MAX(IF(g.gate = 1, g.answer, NULL)) AS g1_answer,
    MAX(IF(g.gate = 1, g.not_asked_reason, NULL)) AS g1_not_asked_reason,
    MAX(IF(g.gate = 2, g.answer, NULL)) AS g2_answer,
    MAX(IF(g.gate = 2, g.choice, NULL)) AS g2_choice
  FROM `keepwell_analytics.consent_gate` g
  JOIN `keepwell_analytics.ticket` t ON t.id = g.ticket_id
  WHERE t.job_type = 'repair'
  GROUP BY g.centre_id, g.ticket_id
)
SELECT
  centre_id,
  gate_month,
  COUNT(*) AS total_repair_tickets_with_gate,
  COUNTIF(g1_not_asked_reason = 'safety_flag') AS skipped_for_safety,
  COUNTIF(g1_answer != 'not_asked') AS gate1_asked,
  COUNTIF(g1_answer = 'yes') AS gate1_yes,
  COUNTIF(g1_answer = 'no') AS gate1_no,
  COUNTIF(g1_answer = 'silence') AS gate1_silence,
  COUNTIF(g1_answer = 'yes' AND g2_answer != 'not_asked') AS gate2_asked,
  COUNTIF(g2_choice = 'switch_to_video') AS gate2_switch_to_video,
  COUNTIF(g2_choice = 'continue_here') AS gate2_continue_here,
  SAFE_DIVIDE(COUNTIF(g1_answer = 'yes'), COUNTIF(g1_answer != 'not_asked')) AS gate1_accept_rate,
  SAFE_DIVIDE(COUNTIF(g2_choice = 'switch_to_video'), COUNTIF(g1_answer = 'yes' AND g2_answer != 'not_asked')) AS gate2_video_rate
FROM gates_pivoted
GROUP BY centre_id, gate_month;

-- ----------------------------------------------------------------------------
-- 5. Urgency Agreement (Agent vs Centre Console Reclassifications)
--    Contract C11: share of tickets whose agent-set urgency class was not
--    changed by the centre.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW `keepwell_analytics.v_urgency_agreement` AS
WITH agent_initial AS (
  SELECT
    ticket_id,
    centre_id,
    class AS agent_class,
    created_at,
    ROW_NUMBER() OVER (PARTITION BY ticket_id ORDER BY created_at ASC) AS rn
  FROM `keepwell_analytics.urgency_assessment`
  WHERE assessed_by = 'agent'
),
console_latest AS (
  SELECT
    ticket_id,
    class AS console_class,
    reason AS override_reason,
    ROW_NUMBER() OVER (PARTITION BY ticket_id ORDER BY created_at DESC) AS rn
  FROM `keepwell_analytics.urgency_assessment`
  WHERE assessed_by = 'centre_console'
)
SELECT
  ai.centre_id,
  DATE_TRUNC(DATE(ai.created_at, 'Asia/Kolkata'), MONTH) AS assessment_month,
  ai.agent_class,
  COUNT(*) AS agent_assessed_tickets,
  COUNTIF(cl.ticket_id IS NULL OR cl.console_class = ai.agent_class) AS agreed_count,
  COUNTIF(cl.ticket_id IS NOT NULL AND cl.console_class != ai.agent_class) AS reclassified_count,
  SAFE_DIVIDE(
    COUNTIF(cl.ticket_id IS NULL OR cl.console_class = ai.agent_class),
    COUNT(*)
  ) AS urgency_agreement_rate
FROM agent_initial ai
LEFT JOIN console_latest cl ON cl.ticket_id = ai.ticket_id AND cl.rn = 1
WHERE ai.rn = 1
GROUP BY ai.centre_id, assessment_month, ai.agent_class;

-- ----------------------------------------------------------------------------
-- 6. Override Rate (Reassignments & Reclassifications per 100 Assigned Tickets)
--    Contract C11: training signal for centre disagreements with the agent.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW `keepwell_analytics.v_override_rate` AS
WITH assigned_tickets AS (
  SELECT
    centre_id,
    DATE_TRUNC(DATE(created_at, 'Asia/Kolkata'), MONTH) AS activity_month,
    COUNT(DISTINCT ticket_id) AS assigned_ticket_count,
    COUNTIF(outcome = 'chosen' AND chosen_by = 'centre_console') AS reassignment_count
  FROM `keepwell_analytics.assignment_candidate`
  WHERE outcome = 'chosen'
  GROUP BY centre_id, activity_month
),
reclassifications AS (
  SELECT
    centre_id,
    DATE_TRUNC(DATE(created_at, 'Asia/Kolkata'), MONTH) AS activity_month,
    COUNT(*) AS reclassification_count
  FROM `keepwell_analytics.urgency_assessment`
  WHERE assessed_by = 'centre_console'
  GROUP BY centre_id, activity_month
)
SELECT
  a.centre_id,
  a.activity_month,
  a.assigned_ticket_count,
  a.reassignment_count,
  COALESCE(r.reclassification_count, 0) AS reclassification_count,
  a.reassignment_count + COALESCE(r.reclassification_count, 0) AS total_overrides,
  SAFE_DIVIDE(
    100.0 * (a.reassignment_count + COALESCE(r.reclassification_count, 0)),
    a.assigned_ticket_count
  ) AS overrides_per_100_assigned
FROM assigned_tickets a
LEFT JOIN reclassifications r
  ON r.centre_id = a.centre_id AND r.activity_month = a.activity_month;

-- ----------------------------------------------------------------------------
-- 7. Technician Utilisation (Jobs per Technician-Day)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW `keepwell_analytics.v_technician_utilisation` AS
SELECT
  v.centre_id,
  v.technician_id,
  DATE(v.planned_start, 'Asia/Kolkata') AS work_date,
  DATE_TRUNC(DATE(v.planned_start, 'Asia/Kolkata'), MONTH) AS work_month,
  COUNT(*) AS jobs_scheduled,
  COUNTIF(v.outcome IS NOT NULL) AS jobs_completed,
  COUNTIF(v.outcome = 'fixed') AS jobs_fixed,
  SUM(
    IF(
      v.check_in_at IS NOT NULL AND v.check_out_at IS NOT NULL,
      TIMESTAMP_DIFF(v.check_out_at, v.check_in_at, MINUTE),
      NULL
    )
  ) AS onsite_minutes
FROM `keepwell_analytics.visit` v
GROUP BY v.centre_id, v.technician_id, work_date, work_month;

-- ----------------------------------------------------------------------------
-- 8. Parts Ready at Visit
--    Contract C11: share of visits where every part in the plan was available
--    at the planned source when the visit started.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW `keepwell_analytics.v_parts_ready_at_visit` AS
WITH latest_plan AS (
  SELECT
    vp.id AS visit_plan_id,
    vp.ticket_id,
    ROW_NUMBER() OVER (PARTITION BY vp.ticket_id ORDER BY vp.version DESC) AS rn
  FROM `keepwell_analytics.visit_plan` vp
),
visit_part_readiness AS (
  SELECT
    v.id AS visit_id,
    v.centre_id,
    v.technician_id,
    DATE_TRUNC(DATE(v.planned_start, 'Asia/Kolkata'), MONTH) AS visit_month,
    COUNT(pp.part_id) AS planned_parts_count,
    COUNTIF(
      EXISTS (
        SELECT 1
        FROM `keepwell_analytics.reservation` r
        WHERE r.visit_id = v.id
          AND r.part_id = pp.part_id
          AND r.quantity >= pp.quantity
          AND r.status IN ('confirmed', 'collected')
      )
      OR EXISTS (
        SELECT 1
        FROM `keepwell_analytics.stock` s
        WHERE s.part_id = pp.part_id
          AND s.quantity >= pp.quantity
          AND (
            (s.holder_type = 'van' AND s.holder_id = v.technician_id)
            OR (s.holder_type = 'centre' AND s.holder_id = v.centre_id)
          )
      )
    ) AS ready_parts_count
  FROM `keepwell_analytics.visit` v
  JOIN latest_plan lp ON lp.ticket_id = v.ticket_id AND lp.rn = 1
  JOIN `keepwell_analytics.plan_part` pp ON pp.visit_plan_id = lp.visit_plan_id
  WHERE v.check_in_at IS NOT NULL OR v.outcome IS NOT NULL
  GROUP BY v.id, v.centre_id, v.technician_id, visit_month
)
SELECT
  centre_id,
  visit_month,
  COUNT(*) AS visits_requiring_parts,
  COUNTIF(ready_parts_count = planned_parts_count) AS visits_all_parts_ready,
  SAFE_DIVIDE(COUNTIF(ready_parts_count = planned_parts_count), COUNT(*)) AS parts_ready_at_visit_rate
FROM visit_part_readiness
GROUP BY centre_id, visit_month;

-- ----------------------------------------------------------------------------
-- 9. Repeat Failures by Model
--    Brand portal quality signal: repeat repair tickets within 14d and 30d
--    grouped by brand, category, model_code, series, and fault_family.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW `keepwell_analytics.v_repeat_failures_by_model` AS
WITH repair_seq AS (
  SELECT
    t.id AS ticket_id,
    t.appliance_id,
    a.brand_id,
    b.name AS brand_name,
    a.category_code,
    am.model_code,
    am.series AS model_series,
    COALESCE(JSON_VALUE(t.case_card, '$.fault_family'), 'unknown') AS fault_family,
    t.created_at,
    LAG(t.created_at) OVER (
      PARTITION BY t.appliance_id, COALESCE(JSON_VALUE(t.case_card, '$.fault_family'), 'unknown')
      ORDER BY t.created_at
    ) AS prev_ticket_at
  FROM `keepwell_analytics.ticket` t
  JOIN `keepwell_analytics.appliance` a ON a.id = t.appliance_id
  JOIN `keepwell_analytics.brand` b ON b.id = a.brand_id
  LEFT JOIN `keepwell_analytics.appliance_model` am ON am.id = a.model_id
  WHERE t.job_type = 'repair'
)
SELECT
  brand_id,
  brand_name,
  category_code,
  COALESCE(model_code, 'unknown') AS model_code,
  COALESCE(model_series, 'unknown') AS model_series,
  fault_family,
  COUNT(*) AS total_repair_tickets,
  COUNTIF(prev_ticket_at IS NOT NULL AND TIMESTAMP_DIFF(created_at, prev_ticket_at, DAY) <= 14) AS repeat_14d_tickets,
  COUNTIF(prev_ticket_at IS NOT NULL AND TIMESTAMP_DIFF(created_at, prev_ticket_at, DAY) <= 30) AS repeat_30d_tickets,
  SAFE_DIVIDE(
    COUNTIF(prev_ticket_at IS NOT NULL AND TIMESTAMP_DIFF(created_at, prev_ticket_at, DAY) <= 14),
    COUNT(*)
  ) AS repeat_14d_rate,
  SAFE_DIVIDE(
    COUNTIF(prev_ticket_at IS NOT NULL AND TIMESTAMP_DIFF(created_at, prev_ticket_at, DAY) <= 30),
    COUNT(*)
  ) AS repeat_30d_rate
FROM repair_seq
GROUP BY brand_id, brand_name, category_code, model_code, model_series, fault_family;

-- ----------------------------------------------------------------------------
-- 10. Response Time to First Reply
--     Measures latency (seconds) from ticket creation to first agent action
--     (first clarifying Q&A, consent gate, or urgency assessment).
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW `keepwell_analytics.v_response_time_first_reply` AS
WITH first_action AS (
  SELECT
    t.id AS ticket_id,
    t.centre_id,
    t.trigger,
    t.channel,
    DATE_TRUNC(DATE(t.created_at, 'Asia/Kolkata'), MONTH) AS ticket_month,
    t.created_at,
    LEAST(
      COALESCE((SELECT MIN(qa.asked_at) FROM `keepwell_analytics.clarifying_qa` qa WHERE qa.ticket_id = t.id), TIMESTAMP '9999-12-31 00:00:00 UTC'),
      COALESCE((SELECT MIN(cg.asked_at) FROM `keepwell_analytics.consent_gate` cg WHERE cg.ticket_id = t.id), TIMESTAMP '9999-12-31 00:00:00 UTC'),
      COALESCE((SELECT MIN(ua.created_at) FROM `keepwell_analytics.urgency_assessment` ua WHERE ua.ticket_id = t.id), TIMESTAMP '9999-12-31 00:00:00 UTC')
    ) AS first_reply_at
  FROM `keepwell_analytics.ticket` t
),
latencies AS (
  SELECT
    centre_id,
    trigger,
    channel,
    ticket_month,
    GREATEST(TIMESTAMP_DIFF(first_reply_at, created_at, SECOND), 0) AS first_reply_seconds
  FROM first_action
  WHERE first_reply_at < TIMESTAMP '9999-12-31 00:00:00 UTC'
)
SELECT
  centre_id,
  trigger,
  channel,
  ticket_month,
  COUNT(*) AS replied_tickets,
  AVG(first_reply_seconds) AS avg_first_reply_seconds,
  APPROX_QUANTILES(first_reply_seconds, 100)[OFFSET(50)] AS p50_first_reply_seconds,
  APPROX_QUANTILES(first_reply_seconds, 100)[OFFSET(90)] AS p90_first_reply_seconds
FROM latencies
GROUP BY centre_id, trigger, channel, ticket_month;
