-- =====================================================================
-- Migration 001: Keepwell Part A Additive Schema Extensions
-- Reversible additive changes only (keepwell_schema.sql stays unmodified).
-- =====================================================================

BEGIN;
SET search_path = kw, public;

-- 1. Appliance evidence level (service-evidence standard)
ALTER TABLE appliance
  ADD COLUMN IF NOT EXISTS evidence_level text NOT NULL DEFAULT 'unverified'
  CHECK (evidence_level IN ('confirmed', 'probable', 'unverified'));

-- 2. Technician spoken close-out debrief
CREATE TABLE IF NOT EXISTS visit_debrief (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  centre_id       uuid NOT NULL DEFAULT current_centre() REFERENCES service_centre(id),
  visit_id        uuid NOT NULL UNIQUE REFERENCES visit(id) ON DELETE CASCADE,
  status          text NOT NULL DEFAULT 'processing' CHECK (status IN ('processing', 'ready', 'confirmed')),
  language        text NOT NULL DEFAULT 'en',
  media_ref       text,
  transcript      text,
  extracted       jsonb NOT NULL DEFAULT '{}',
  unresolved      jsonb NOT NULL DEFAULT '[]',
  confirmed_at    timestamptz,
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now()
);

-- 3. Payment intents (UPI intent + Google Pay for Web)
CREATE TABLE IF NOT EXISTS payment_intent (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  centre_id       uuid NOT NULL DEFAULT current_centre() REFERENCES service_centre(id),
  quote_id        uuid NOT NULL REFERENCES quote(id) ON DELETE CASCADE,
  ticket_id       uuid NOT NULL REFERENCES ticket(id) ON DELETE CASCADE,
  amount_paise    bigint NOT NULL CHECK (amount_paise >= 0),
  status          text NOT NULL DEFAULT 'created' CHECK (status IN ('created', 'pending', 'paid', 'failed', 'expired')),
  method          text NOT NULL CHECK (method IN ('upi_intent', 'google_pay')),
  upi_intent_url  text,
  google_pay_json jsonb,
  payment_ref     text,
  created_at      timestamptz NOT NULL DEFAULT now(),
  expires_at      timestamptz NOT NULL,
  paid_at         timestamptz
);

-- 4. FCM Device Tokens
CREATE TABLE IF NOT EXISTS device_token (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  centre_id       uuid REFERENCES service_centre(id),
  user_id         text NOT NULL,
  role            text NOT NULL,
  token           text NOT NULL UNIQUE,
  platform        text NOT NULL DEFAULT 'web',
  updated_at      timestamptz NOT NULL DEFAULT now()
);

-- 5. Transactional Outbox for Firestore projections & Pub/Sub events
CREATE TABLE IF NOT EXISTS outbox_event (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  centre_id       uuid,
  ticket_id       uuid,
  conversation_id uuid,
  event_type      text NOT NULL,
  actor           text NOT NULL DEFAULT 'system',
  title           text NOT NULL,
  detail          text NOT NULL DEFAULT '',
  payload         jsonb NOT NULL DEFAULT '{}',
  processed_at    timestamptz,
  created_at      timestamptz NOT NULL DEFAULT now()
);

-- 6. DB-level consent gate enforcement triggers
CREATE OR REPLACE FUNCTION enforce_fix_attempt_gate1() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM consent_gate
    WHERE ticket_id = NEW.ticket_id AND gate = 1 AND answer = 'yes'
  ) THEN
    RAISE EXCEPTION 'fix_attempt requires consent_gate 1 = yes for ticket %', NEW.ticket_id;
  END IF;
  RETURN NEW;
END $$;

DROP TRIGGER IF EXISTS fix_attempt_requires_gate1 ON fix_attempt;
CREATE TRIGGER fix_attempt_requires_gate1
  BEFORE INSERT ON fix_attempt
  FOR EACH ROW EXECUTE FUNCTION enforce_fix_attempt_gate1();

CREATE OR REPLACE FUNCTION enforce_video_session_gate2() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.video_on THEN
    IF NOT EXISTS (
      SELECT 1 FROM consent_gate
      WHERE ticket_id = NEW.ticket_id AND gate = 2 AND answer = 'yes' AND choice = 'switch_to_video'
    ) THEN
      RAISE EXCEPTION 'video diagnosis_session requires consent_gate 2 = switch_to_video for ticket %', NEW.ticket_id;
    END IF;
  END IF;
  RETURN NEW;
END $$;

DROP TRIGGER IF EXISTS diagnosis_session_requires_gate2 ON diagnosis_session;
CREATE TRIGGER diagnosis_session_requires_gate2
  BEFORE INSERT ON diagnosis_session
  FOR EACH ROW EXECUTE FUNCTION enforce_video_session_gate2();

-- 7. FVR-14 View (Contract Section 11)
CREATE OR REPLACE VIEW fvr_14d AS
SELECT
  f.ticket_id,
  f.visit_id,
  f.technician_id,
  f.centre_id,
  f.category_code,
  f.brand_id,
  t.appliance_id,
  t.closure_confirmed_at,
  (
    f.fixed_first_time
    AND t.closure_confirmed_at IS NOT NULL
    AND NOT EXISTS (
      SELECT 1 FROM ticket t2
      WHERE t2.appliance_id = t.appliance_id
        AND t2.id <> t.id
        AND t2.job_type = 'repair'
        AND t2.created_at > t.closure_confirmed_at
        AND t2.created_at <= t.closure_confirmed_at + interval '14 days'
    )
  ) AS resolved_fvr_14d
FROM first_visit_outcome f
JOIN ticket t ON t.id = f.ticket_id;

-- 8. RLS on new centre-owned tables
ALTER TABLE visit_debrief ENABLE ROW LEVEL SECURITY;
CREATE POLICY centre_isolation ON visit_debrief
  USING (centre_id = current_centre() OR is_platform())
  WITH CHECK (centre_id = current_centre() OR is_platform());

ALTER TABLE payment_intent ENABLE ROW LEVEL SECURITY;
CREATE POLICY centre_isolation ON payment_intent
  USING (centre_id = current_centre() OR is_platform())
  WITH CHECK (centre_id = current_centre() OR is_platform());

GRANT SELECT, INSERT, UPDATE ON visit_debrief, payment_intent, device_token, outbox_event TO kw_app;

COMMIT;
