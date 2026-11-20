-- =====================================================================
-- Keepwell schema v0.2  (platform model)
-- Target: PostgreSQL 15+ (Cloud SQL for PostgreSQL)
-- Extensions: postgis, vector (pgvector), pgcrypto, btree_gist
-- Money is stored in paise (bigint, INR). Times are timestamptz.
-- Statements tagged "-- @geo" or "-- @vec" need PostGIS or pgvector.
--
-- One shared database for every service centre on the platform.
--   * Identity is global: one Keepwell id per household (verified phone)
--     and per appliance (brand + normalised serial). Numbers that belong
--     to a centre, a brand or a retailer are alias rows in external_ref.
--   * Operational rows carry centre_id and are isolated with row-level
--     security. The agent connects as kw_app and sets kw.centre_id for
--     the centre whose line it is answering.
--   * Technical history crosses centres only through
--     kw.read_shared_history(), which checks consent and writes access_log.
--   * Prices, notes and settlements are private to the centre that
--     created them.
-- Starting values (weights, thresholds, rules) live in scoring_config and
-- urgency_rule rows, not in this file.
-- =====================================================================

BEGIN;

CREATE EXTENSION IF NOT EXISTS postgis;     -- @geo
CREATE EXTENSION IF NOT EXISTS vector;      -- @vec
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS btree_gist;

CREATE SCHEMA IF NOT EXISTS kw;
SET search_path = kw, public;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'kw_app') THEN
    CREATE ROLE kw_app NOLOGIN;
  END IF;
END $$;

-- ---------------------------------------------------------------------
-- 0. Helper functions
-- ---------------------------------------------------------------------
CREATE FUNCTION touch_updated_at() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  NEW.updated_at := now();
  RETURN NEW;
END $$;

CREATE FUNCTION deny_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION '% is append-only', TG_TABLE_NAME;
END $$;

-- Session context set by the agent for each call or conversation:
--   SET kw.centre_id = '<uuid>';        the centre whose line this is
--   SET kw.role = 'platform';           Keepwell operations and batch jobs only
CREATE FUNCTION current_centre() RETURNS uuid LANGUAGE plpgsql STABLE AS $$
BEGIN
  RETURN nullif(current_setting('kw.centre_id', true), '')::uuid;
END $$;

CREATE FUNCTION is_platform() RETURNS boolean LANGUAGE plpgsql STABLE AS $$
BEGIN
  RETURN coalesce(current_setting('kw.role', true), '') = 'platform';
END $$;

-- ---------------------------------------------------------------------
-- 1. Reference data: catalogue (L1), policy and price (L4), safe fixes (L6)
-- ---------------------------------------------------------------------
CREATE TABLE brand (
  id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name                text NOT NULL UNIQUE,
  forwarding_enabled  boolean NOT NULL DEFAULT false,   -- brand can forward requests to a centre
  created_at          timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE appliance_category (
  code        text PRIMARY KEY,
  name        text NOT NULL
);

CREATE TABLE category_norm (
  id                       uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  category_code            text NOT NULL REFERENCES appliance_category(code),
  service_interval_months  smallint NOT NULL CHECK (service_interval_months > 0),
  typical_life_years       smallint NOT NULL CHECK (typical_life_years > 0),
  valid_from               date NOT NULL,
  valid_to                 date,
  CHECK (valid_to IS NULL OR valid_to > valid_from),
  EXCLUDE USING gist (category_code WITH =, daterange(valid_from, valid_to) WITH &&)
);

CREATE TABLE appliance_model (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id       uuid NOT NULL REFERENCES brand(id),
  category_code  text NOT NULL REFERENCES appliance_category(code),
  model_code     text NOT NULL,
  series         text,
  year_from      smallint,
  specs          jsonb NOT NULL DEFAULT '{}',
  created_at     timestamptz NOT NULL DEFAULT now(),
  UNIQUE (brand_id, model_code)
);

-- Platform reference visit fee and labour (benchmark). Each centre's own
-- prices are in centre_price and are private to that centre.
CREATE TABLE rate_card (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  category_code     text NOT NULL REFERENCES appliance_category(code),
  job_type          text NOT NULL CHECK (job_type IN (
                      'installation','preventive_service','repair',
                      'coverage_claim','uninstall_reinstall','inspection_advice')),
  complexity_band   text NOT NULL CHECK (complexity_band IN ('basic','standard','complex')),
  visit_fee_paise   bigint NOT NULL CHECK (visit_fee_paise >= 0),
  labour_paise      bigint NOT NULL CHECK (labour_paise >= 0),
  valid_from        date NOT NULL,
  valid_to          date,
  CHECK (valid_to IS NULL OR valid_to > valid_from),
  UNIQUE (category_code, job_type, complexity_band, valid_from)
);

CREATE TABLE kb_document (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  title             text NOT NULL,
  brand_id          uuid REFERENCES brand(id),
  category_code     text REFERENCES appliance_category(code),
  model_series      text,
  doc_type          text NOT NULL CHECK (doc_type IN (
                      'manual','error_codes','troubleshooting','installation',
                      'bulletin','parts_view','warranty_terms','amc_terms','safe_fix')),
  language          text NOT NULL DEFAULT 'en',
  version_year      smallint,
  valid_to          date,
  authority         text NOT NULL CHECK (authority IN ('oem','centre_verified','keepwell')),
  audience          text NOT NULL DEFAULT 'technician' CHECK (audience IN ('technician','household','both')),
  storage_uri       text NOT NULL,
  file_search_store text,
  file_search_doc   text,
  rights_status     text NOT NULL DEFAULT 'pending' CHECK (rights_status IN ('confirmed','pending','none')),
  created_at        timestamptz NOT NULL DEFAULT now(),
  updated_at        timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE coverage_plan (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  kind          text NOT NULL CHECK (kind IN ('brand_warranty','extended_warranty','amc')),
  provider_name text NOT NULL,
  brand_id      uuid REFERENCES brand(id),
  terms_doc_id  uuid REFERENCES kb_document(id),
  covers        jsonb NOT NULL DEFAULT '{}',
  created_at    timestamptz NOT NULL DEFAULT now()
);

-- Layer 6. A fix the agent may guide a household through. The CHECK
-- constraints are the safe-fix threshold from the design document: a fix
-- that breaks them cannot be stored as active.
CREATE TABLE safe_fix_catalogue (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code             text NOT NULL UNIQUE,
  category_code    text NOT NULL REFERENCES appliance_category(code),
  brand_id         uuid REFERENCES brand(id),          -- null = any brand
  model_series     text,                                -- null = any series
  fault_family     text NOT NULL,
  title            text NOT NULL,
  symptom_terms    text[] NOT NULL DEFAULT '{}',
  steps            jsonb NOT NULL,                      -- [{n, say, check}]
  step_count       smallint NOT NULL CHECK (step_count BETWEEN 1 AND 6),
  est_minutes      smallint NOT NULL CHECK (est_minutes BETWEEN 1 AND 12),
  reversible       boolean NOT NULL DEFAULT true,
  needs_tools      boolean NOT NULL DEFAULT false,
  opens_panel      boolean NOT NULL DEFAULT false,
  manual_doc_id    uuid REFERENCES kb_document(id),
  manual_page      smallint,
  worst_case       text NOT NULL,                       -- stated worst outcome of doing the fix
  reviewer_name    text,
  reviewer_role    text,
  reviewed_on      date,
  review_due       date,
  status           text NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','active','review_due','retired')),
  created_at       timestamptz NOT NULL DEFAULT now(),
  CHECK (jsonb_array_length(steps) = step_count),
  CHECK (status <> 'active' OR (reversible AND NOT needs_tools AND reviewer_name IS NOT NULL AND reviewed_on IS NOT NULL AND manual_doc_id IS NOT NULL)),
  CHECK (NOT opens_panel OR manual_doc_id IS NOT NULL)
);

-- Rules the agent applies to set an urgency class. Starting values only.
CREATE TABLE urgency_rule (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code         text NOT NULL UNIQUE,
  class        text NOT NULL CHECK (class IN ('safety','urgent','standard','planned')),
  category_code text REFERENCES appliance_category(code),   -- null = any category
  description  text NOT NULL,
  condition    jsonb NOT NULL DEFAULT '{}',                 -- facts that must be true
  protective_message text,                                  -- sent at once when the rule fires
  source       text NOT NULL DEFAULT 'keepwell_hypothesis' CHECK (source IN ('keepwell_hypothesis','oem','centre','regulation')),
  active       boolean NOT NULL DEFAULT true,
  created_at   timestamptz NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------
-- 2. Parties: centres, brands' retailers, parts network
-- ---------------------------------------------------------------------
CREATE TABLE service_centre (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name              text NOT NULL,
  address_line      text NOT NULL,
  pincode           text NOT NULL,
  location          geography(Point,4326),                -- @geo
  service_pincodes  text[] NOT NULL DEFAULT '{}',
  categories        text[] NOT NULL DEFAULT '{}',
  hours             jsonb NOT NULL DEFAULT '{}',
  default_language  text NOT NULL DEFAULT 'en',
  onboarding_status text NOT NULL DEFAULT 'invited' CHECK (onboarding_status IN (
                      'invited','documents_pending','verified','active','suspended')),
  created_at        timestamptz NOT NULL DEFAULT now(),
  updated_at        timestamptz NOT NULL DEFAULT now()
);

-- Private to the centre: commercial terms with Keepwell.
CREATE TABLE centre_commercial (
  centre_id         uuid PRIMARY KEY REFERENCES service_centre(id),
  commission_terms  jsonb NOT NULL DEFAULT '{}',
  payout_ref        text
);

-- The numbers and lines Keepwell answers on for a centre (one WhatsApp number per centre).
CREATE TABLE centre_channel (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  centre_id     uuid NOT NULL REFERENCES service_centre(id),
  channel       text NOT NULL CHECK (channel IN ('voice','whatsapp','sms')),
  number_ref    text NOT NULL,                  -- number as dialled by households
  provider_ref  text,
  status        text NOT NULL DEFAULT 'active' CHECK (status IN ('pending','active','paused')),
  UNIQUE (channel, number_ref)
);

-- Which brands a centre may service and at what level. The agent checks
-- this before it accepts a job; it never recommends a centre.
CREATE TABLE centre_brand_authorisation (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  centre_id   uuid NOT NULL REFERENCES service_centre(id),
  brand_id    uuid NOT NULL REFERENCES brand(id),
  level       text NOT NULL CHECK (level IN ('authorised_service','installation_only','independent')),
  valid_from  date NOT NULL,
  valid_to    date,
  evidence_ref text,
  CHECK (valid_to IS NULL OR valid_to > valid_from),
  UNIQUE (centre_id, brand_id, level, valid_from)
);

CREATE TABLE centre_capacity (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  centre_id      uuid NOT NULL REFERENCES service_centre(id),
  category_code  text NOT NULL REFERENCES appliance_category(code),
  job_type       text NOT NULL,
  daily_slots    smallint NOT NULL CHECK (daily_slots >= 0),
  urgent_holdback smallint NOT NULL DEFAULT 0 CHECK (urgent_holdback >= 0),
  UNIQUE (centre_id, category_code, job_type)
);

-- Private to the centre: its own visit fee and labour.
CREATE TABLE centre_price (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  centre_id         uuid NOT NULL DEFAULT current_centre() REFERENCES service_centre(id),
  category_code     text NOT NULL REFERENCES appliance_category(code),
  job_type          text NOT NULL,
  complexity_band   text NOT NULL CHECK (complexity_band IN ('basic','standard','complex')),
  visit_fee_paise   bigint NOT NULL CHECK (visit_fee_paise >= 0),
  labour_paise      bigint NOT NULL CHECK (labour_paise >= 0),
  valid_from        date NOT NULL,
  valid_to          date,
  CHECK (valid_to IS NULL OR valid_to > valid_from),
  UNIQUE (centre_id, category_code, job_type, complexity_band, valid_from)
);

CREATE TABLE retailer (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name        text NOT NULL,
  city        text,
  created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE technician (
  id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  centre_id           uuid NOT NULL DEFAULT current_centre() REFERENCES service_centre(id),
  name                text NOT NULL,
  phone_enc           bytea NOT NULL,
  phone_hash          bytea NOT NULL UNIQUE,
  languages           text[] NOT NULL DEFAULT '{}',
  shift_start         time NOT NULL DEFAULT '09:00',
  shift_end           time NOT NULL DEFAULT '18:00',
  route_anchor_type   text NOT NULL DEFAULT 'centre' CHECK (route_anchor_type IN ('centre','home','custom')),
  route_anchor        geography(Point,4326),               -- @geo
  vehicle_type        text,
  tool_kit            text[] NOT NULL DEFAULT '{}',
  identity_verified   boolean NOT NULL DEFAULT false,
  safety_certs        text[] NOT NULL DEFAULT '{}',
  active              boolean NOT NULL DEFAULT true,
  created_at          timestamptz NOT NULL DEFAULT now(),
  updated_at          timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE technician_skill (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  technician_id  uuid NOT NULL REFERENCES technician(id) ON DELETE CASCADE,
  centre_id      uuid NOT NULL DEFAULT current_centre() REFERENCES service_centre(id),
  brand_id       uuid REFERENCES brand(id),
  category_code  text NOT NULL REFERENCES appliance_category(code),
  fault_class    text NOT NULL,
  level          smallint NOT NULL CHECK (level BETWEEN 1 AND 5),
  certified_on   date,
  certificate_ref text
);
CREATE UNIQUE INDEX technician_skill_uq
  ON technician_skill (technician_id, COALESCE(brand_id, '00000000-0000-0000-0000-000000000000'::uuid), category_code, fault_class);

CREATE TABLE technician_availability (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  technician_id  uuid NOT NULL REFERENCES technician(id) ON DELETE CASCADE,
  centre_id      uuid NOT NULL DEFAULT current_centre() REFERENCES service_centre(id),
  slot_start     timestamptz NOT NULL,
  slot_end       timestamptz NOT NULL,
  status         text NOT NULL DEFAULT 'open' CHECK (status IN ('open','held','booked','blocked')),
  held_until     timestamptz,
  visit_id       uuid,
  CHECK (slot_end > slot_start),
  EXCLUDE USING gist (technician_id WITH =, tstzrange(slot_start, slot_end) WITH &&)
);

CREATE TABLE technician_metrics (
  technician_id          uuid NOT NULL REFERENCES technician(id) ON DELETE CASCADE,
  centre_id              uuid NOT NULL DEFAULT current_centre() REFERENCES service_centre(id),
  category_code          text NOT NULL,
  period_end             date NOT NULL,
  jobs                   integer NOT NULL CHECK (jobs >= 0),
  first_time_fix_rate    numeric(5,4) CHECK (first_time_fix_rate BETWEEN 0 AND 1),
  on_time_rate           numeric(5,4) CHECK (on_time_rate BETWEEN 0 AND 1),
  repeat_visit_rate_30d  numeric(5,4) CHECK (repeat_visit_rate_30d BETWEEN 0 AND 1),
  acceptance_rate        numeric(5,4) CHECK (acceptance_rate BETWEEN 0 AND 1),
  avg_quote_variance_pct numeric(7,2),
  computed_at            timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (technician_id, category_code, period_end)
);

CREATE TABLE parts_centre (
  id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name                text NOT NULL,
  address_line        text NOT NULL,
  pincode             text NOT NULL,
  location            geography(Point,4326),               -- @geo
  hours               jsonb NOT NULL DEFAULT '{}',
  pickup_supported    boolean NOT NULL DEFAULT true,
  delivery_supported  boolean NOT NULL DEFAULT false,
  fill_rate           numeric(5,4) CHECK (fill_rate BETWEEN 0 AND 1),
  stock_accuracy      numeric(5,4) CHECK (stock_accuracy BETWEEN 0 AND 1),
  active              boolean NOT NULL DEFAULT true,
  created_at          timestamptz NOT NULL DEFAULT now(),
  updated_at          timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE parts_centre_brand (
  parts_centre_id  uuid NOT NULL REFERENCES parts_centre(id) ON DELETE CASCADE,
  brand_id         uuid NOT NULL REFERENCES brand(id),
  is_authorised    boolean NOT NULL DEFAULT false,
  PRIMARY KEY (parts_centre_id, brand_id)
);

CREATE TABLE part_catalogue (
  id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id            uuid NOT NULL REFERENCES brand(id),
  part_no             text NOT NULL,
  name                text NOT NULL,
  kind                text NOT NULL CHECK (kind IN ('genuine','aftermarket')),
  substitution_group  text,
  mrp_paise           bigint NOT NULL CHECK (mrp_paise >= 0),
  warranty_months     smallint NOT NULL DEFAULT 0,
  UNIQUE (brand_id, part_no)
);

CREATE TABLE part_compatibility (
  part_id   uuid NOT NULL REFERENCES part_catalogue(id) ON DELETE CASCADE,
  model_id  uuid NOT NULL REFERENCES appliance_model(id) ON DELETE CASCADE,
  revision  text NOT NULL DEFAULT '',
  PRIMARY KEY (part_id, model_id, revision)
);

-- centre_id is the owning centre for van and centre stock; null for the
-- shared parts network, whose stock every centre may read.
CREATE TABLE stock (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  holder_type  text NOT NULL CHECK (holder_type IN ('van','centre','parts_centre')),
  holder_id    uuid NOT NULL,
  centre_id    uuid REFERENCES service_centre(id),
  part_id      uuid NOT NULL REFERENCES part_catalogue(id),
  quantity     integer NOT NULL CHECK (quantity >= 0),
  as_of        timestamptz NOT NULL DEFAULT now(),
  source       text NOT NULL CHECK (source IN ('scan','call','feed','manual')),
  confidence   numeric(3,2) NOT NULL DEFAULT 0.50 CHECK (confidence BETWEEN 0 AND 1),
  UNIQUE (holder_type, holder_id, part_id),
  CHECK ((holder_type = 'parts_centre') = (centre_id IS NULL))
);

-- ---------------------------------------------------------------------
-- 3. Identity and memory: global households and appliances
-- ---------------------------------------------------------------------
CREATE TABLE community (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name          text NOT NULL,
  pincode       text NOT NULL,
  location      geography(Point,4326),        -- @geo
  contact_ref   text,
  created_at    timestamptz NOT NULL DEFAULT now()
);

-- One row per household across all centres. The key is the verified phone.
CREATE TABLE household (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  phone_enc         bytea NOT NULL,
  phone_hash        bytea NOT NULL UNIQUE,
  phone_verified_at timestamptz,                          -- null = provisional record
  verified_via      text CHECK (verified_via IN ('call_line','otp','brand_record','retailer_record')),
  language          text NOT NULL DEFAULT 'en',
  address_line      text,
  pincode           text,
  location          geography(Point,4326),                -- @geo
  location_verified boolean NOT NULL DEFAULT false,
  community_id      uuid REFERENCES community(id),
  access_notes      jsonb NOT NULL DEFAULT '{}',
  preferred_slots   jsonb NOT NULL DEFAULT '{}',
  status            text NOT NULL DEFAULT 'active' CHECK (status IN ('active','paused','closed','merged')),
  merged_into_id    uuid REFERENCES household(id),
  created_at        timestamptz NOT NULL DEFAULT now(),
  updated_at        timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE household_member (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  household_id      uuid NOT NULL REFERENCES household(id) ON DELETE CASCADE,
  name              text,
  phone_enc         bytea NOT NULL,
  phone_hash        bytea NOT NULL UNIQUE,
  role              text NOT NULL DEFAULT 'family' CHECK (role IN ('owner','family','tenant')),
  may_raise_ticket  boolean NOT NULL DEFAULT true,
  created_at        timestamptz NOT NULL DEFAULT now()
);

-- Which centres have served or been contacted by a household. This link is
-- what lets a centre see the household record, and it records the centre
-- that last served the household: only that centre sends reminders.
CREATE TABLE household_centre_link (
  household_id      uuid NOT NULL REFERENCES household(id) ON DELETE CASCADE,
  centre_id         uuid NOT NULL REFERENCES service_centre(id),
  first_contact_at  timestamptz NOT NULL,
  last_served_at    timestamptz,
  contact_count     integer NOT NULL DEFAULT 1,
  PRIMARY KEY (household_id, centre_id)
);

-- One row per physical appliance. Verified rows are keyed by brand + serial.
-- A provisional row (no serial yet) is merged later through identity_merge.
CREATE TABLE appliance (
  id                      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  household_id            uuid NOT NULL REFERENCES household(id) ON DELETE CASCADE,
  category_code           text NOT NULL REFERENCES appliance_category(code),
  brand_id                uuid NOT NULL REFERENCES brand(id),
  model_id                uuid REFERENCES appliance_model(id),
  model_text              text,
  serial_no               text,
  serial_norm             text,                                   -- upper-case, no spaces or dashes
  identity_status         text NOT NULL DEFAULT 'provisional' CHECK (identity_status IN ('provisional','verified','merged')),
  merged_into_id          uuid REFERENCES appliance(id),
  first_seen_via          text CHECK (first_seen_via IN ('household','brand','retailer','centre')),
  first_seen_centre_id    uuid REFERENCES service_centre(id),
  purchase_date           date,
  purchase_source         text,
  invoice_file_ref        text,
  install_date            date,
  installed_by            uuid REFERENCES technician(id),
  warranty_start          date,
  warranty_end            date,
  coverage_plan_id        uuid REFERENCES coverage_plan(id),
  usage_profile           jsonb NOT NULL DEFAULT '{}',
  room                    text,
  care_index              smallint CHECK (care_index BETWEEN 0 AND 100),
  care_index_reasons      jsonb NOT NULL DEFAULT '[]',
  care_index_updated_at   timestamptz,
  last_service_at         date,
  last_served_centre_id   uuid REFERENCES service_centre(id),
  next_due_at             date,
  status                  text NOT NULL DEFAULT 'active' CHECK (status IN ('active','retired','sold')),
  created_at              timestamptz NOT NULL DEFAULT now(),
  updated_at              timestamptz NOT NULL DEFAULT now(),
  CHECK (warranty_end IS NULL OR warranty_start IS NULL OR warranty_end >= warranty_start),
  CHECK (identity_status <> 'verified' OR serial_norm IS NOT NULL),
  CHECK ((identity_status = 'merged') = (merged_into_id IS NOT NULL))
);
CREATE UNIQUE INDEX appliance_global_id_uq
  ON appliance (brand_id, serial_norm) WHERE serial_norm IS NOT NULL AND identity_status <> 'merged';

-- Numbers and ids that belong to someone else's system: a centre's own
-- customer number, a brand's case id, a retailer's order id, a phone seen
-- before it was verified. Lookup goes through here so one entity can be
-- found from any party's reference without changing its Keepwell id.
CREATE TABLE external_ref (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  entity_type  text NOT NULL CHECK (entity_type IN ('household','appliance','ticket','centre','technician')),
  entity_id    uuid NOT NULL,
  ref_type     text NOT NULL CHECK (ref_type IN (
                 'phone','serial','order_id','invoice_no','brand_case_id','centre_customer_no','whatsapp_number','email')),
  ref_norm     text NOT NULL,                  -- normalised value; phones are stored as keyed hash (hex)
  owner_type   text NOT NULL CHECK (owner_type IN ('keepwell','centre','brand','retailer')),
  owner_id     uuid,
  verified     boolean NOT NULL DEFAULT false,
  first_seen_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (ref_type, ref_norm, owner_type, owner_id)
);
CREATE INDEX external_ref_entity_idx ON external_ref (entity_type, entity_id);

-- Audit trail for merges. A merge can be reversed; the old row is kept.
CREATE TABLE identity_merge (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  entity_type   text NOT NULL CHECK (entity_type IN ('household','appliance')),
  from_id       uuid NOT NULL,
  into_id       uuid NOT NULL,
  reason        text NOT NULL,
  evidence      jsonb NOT NULL DEFAULT '{}',
  merged_by     text NOT NULL,
  merged_at     timestamptz NOT NULL DEFAULT now(),
  reversed_at   timestamptz,
  CHECK (from_id <> into_id)
);

-- ---------------------------------------------------------------------
-- 4. Configuration
-- ---------------------------------------------------------------------
CREATE TABLE scoring_config (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  kind        text NOT NULL CHECK (kind IN ('assignment','parts_ranking','care_index','batching','urgency')),
  name        text NOT NULL,
  weights     jsonb NOT NULL DEFAULT '{}',
  params      jsonb NOT NULL DEFAULT '{}',
  valid_from  timestamptz NOT NULL DEFAULT now(),
  valid_to    timestamptz,
  created_by  text,
  CHECK (valid_to IS NULL OR valid_to > valid_from)
);

-- ---------------------------------------------------------------------
-- 5. Work: a case from trigger to closure. Every row carries centre_id.
-- ---------------------------------------------------------------------
-- A brand-forwarded request as received.
CREATE TABLE brand_referral (
  id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  centre_id          uuid NOT NULL DEFAULT current_centre() REFERENCES service_centre(id),
  brand_id           uuid NOT NULL REFERENCES brand(id),
  brand_request_ref  text NOT NULL,
  received_at        timestamptz NOT NULL,
  payload            jsonb NOT NULL DEFAULT '{}',
  claimed_entitlement text CHECK (claimed_entitlement IN ('brand_warranty','extended_warranty','amc','none')),
  authority_checked  text CHECK (authority_checked IN ('authorised_service','installation_only','independent','none')),
  household_contacted_at timestamptz,
  status             text NOT NULL DEFAULT 'received' CHECK (status IN ('received','household_contacted','case_opened','declined','duplicate')),
  UNIQUE (brand_id, brand_request_ref)
);

-- A retailer handover (sale with installation or demo).
CREATE TABLE retailer_handover (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  centre_id       uuid NOT NULL DEFAULT current_centre() REFERENCES service_centre(id),
  retailer_id     uuid NOT NULL REFERENCES retailer(id),
  order_ref       text NOT NULL,
  invoice_no      text,
  purchase_date   date,
  requested_job   text NOT NULL CHECK (requested_job IN ('installation','demo','uninstall_reinstall')),
  payload         jsonb NOT NULL DEFAULT '{}',
  received_at     timestamptz NOT NULL,
  status          text NOT NULL DEFAULT 'received' CHECK (status IN ('received','household_contacted','case_opened','declined')),
  UNIQUE (retailer_id, order_ref)
);

CREATE TABLE ticket (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  centre_id         uuid NOT NULL DEFAULT current_centre() REFERENCES service_centre(id),
  household_id      uuid NOT NULL REFERENCES household(id),
  appliance_id      uuid REFERENCES appliance(id),
  trigger           text NOT NULL CHECK (trigger IN ('household_call','household_message','brand_forward','retailer_handover')),
  channel           text NOT NULL CHECK (channel IN ('voice','whatsapp','sms','app','brand_api','retailer_api','centre_console')),
  job_type          text NOT NULL CHECK (job_type IN (
                      'installation','preventive_service','repair',
                      'coverage_claim','uninstall_reinstall','inspection_advice')),
  brand_referral_id uuid REFERENCES brand_referral(id),
  retailer_handover_id uuid REFERENCES retailer_handover(id),
  origin_reminder_id uuid,                                -- set when the household replied to a reminder
  raw_inputs        jsonb NOT NULL DEFAULT '[]',
  case_card         jsonb NOT NULL DEFAULT '{}',
  urgency_class     text NOT NULL DEFAULT 'standard' CHECK (urgency_class IN ('safety','urgent','standard','planned')),
  needed_by         timestamptz,                          -- stated by the household; separate from urgency
  safety_flag       boolean NOT NULL DEFAULT false,
  safety_reason     text,
  entitlement       text CHECK (entitlement IN ('brand_warranty','extended_warranty','amc','paid')),
  coverage_plan_id  uuid REFERENCES coverage_plan(id),
  visit_address     text,
  visit_location    geography(Point,4326),                -- @geo
  status            text NOT NULL DEFAULT 'new' CHECK (status IN (
                      'new','triage','clarifying','self_fix','diagnosed','awaiting_slot','booked','scheduled',
                      'in_progress','needs_part','completed','closed','cancelled','escalated')),
  resolution        text CHECK (resolution IN ('self_fix','visit','advice_only','cancelled','duplicate')),
  first_visit_by    timestamptz,
  closure_otp_ref   text,                                 -- provider reference; the code itself is never stored
  closure_confirmed_at timestamptz,
  created_at        timestamptz NOT NULL DEFAULT now(),
  updated_at        timestamptz NOT NULL DEFAULT now(),
  closed_at         timestamptz,
  CHECK (appliance_id IS NOT NULL OR job_type = 'installation'),
  CHECK (NOT safety_flag OR urgency_class = 'safety'),
  CHECK (status <> 'closed' OR closure_confirmed_at IS NOT NULL),
  CHECK (closure_confirmed_at IS NULL OR closure_otp_ref IS NOT NULL),
  CHECK ((trigger = 'brand_forward') = (brand_referral_id IS NOT NULL)),
  CHECK ((trigger = 'retailer_handover') = (retailer_handover_id IS NOT NULL))
);

-- One row per conversation. A case can have several: a call, then a video
-- session started from it, then a later message.
CREATE TABLE conversation (
  id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  centre_id           uuid NOT NULL DEFAULT current_centre() REFERENCES service_centre(id),
  ticket_id           uuid REFERENCES ticket(id),
  household_id        uuid REFERENCES household(id),
  channel             text NOT NULL CHECK (channel IN ('voice','whatsapp','sms','app','video')),
  modality            text NOT NULL CHECK (modality IN ('voice','text','video')),
  parent_conversation_id uuid REFERENCES conversation(id),
  language            text,
  started_at          timestamptz NOT NULL,
  ended_at            timestamptz,
  end_reason          text CHECK (end_reason IN ('completed','household_left','switched_to_video','link_not_opened','timeout','connection_lost','safety_stop')),
  recording_consent   boolean NOT NULL DEFAULT false,
  transcript_uri      text,
  summary             text
);

CREATE TABLE urgency_assessment (
  id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  centre_id           uuid NOT NULL DEFAULT current_centre() REFERENCES service_centre(id),
  ticket_id           uuid NOT NULL REFERENCES ticket(id) ON DELETE CASCADE,
  class               text NOT NULL CHECK (class IN ('safety','urgent','standard','planned')),
  rule_codes          text[] NOT NULL DEFAULT '{}',
  facts               jsonb NOT NULL DEFAULT '{}',       -- answers to the three fact questions
  assessed_by         text NOT NULL CHECK (assessed_by IN ('agent','centre_console')),
  reason              text NOT NULL,
  protective_steps_sent boolean NOT NULL DEFAULT false,
  created_at          timestamptz NOT NULL DEFAULT now()
);

-- Consent gates asked before any self-fix. Gate 1: okay to try a safe fix.
-- Gate 2: only after a yes, switch to video or carry on here. Silence is no.
CREATE TABLE consent_gate (
  id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  centre_id           uuid NOT NULL DEFAULT current_centre() REFERENCES service_centre(id),
  ticket_id           uuid NOT NULL REFERENCES ticket(id) ON DELETE CASCADE,
  conversation_id     uuid REFERENCES conversation(id),
  gate                smallint NOT NULL CHECK (gate IN (1,2)),
  asked_at            timestamptz NOT NULL,
  answer              text NOT NULL CHECK (answer IN ('yes','no','silence','not_asked')),
  answered_at         timestamptz,
  choice              text CHECK (choice IN ('continue_here','switch_to_video')),
  not_asked_reason    text CHECK (not_asked_reason IN ('safety_flag','job_type','gate1_not_yes','household_unreachable')),
  UNIQUE (ticket_id, gate),
  CHECK ((answer = 'not_asked') = (not_asked_reason IS NOT NULL)),
  CHECK (gate = 2 OR choice IS NULL),
  CHECK (choice IS NULL OR answer = 'yes')
);

CREATE TABLE clarifying_qa (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  centre_id        uuid NOT NULL DEFAULT current_centre() REFERENCES service_centre(id),
  ticket_id        uuid NOT NULL REFERENCES ticket(id) ON DELETE CASCADE,
  conversation_id  uuid REFERENCES conversation(id),
  seq              smallint NOT NULL CHECK (seq > 0),
  question         text NOT NULL,
  answer           text,
  answer_source    text CHECK (answer_source IN ('voice','text','photo','video_observation','brand_payload','retailer_payload','history')),
  asked_at         timestamptz NOT NULL,
  UNIQUE (ticket_id, seq)
);

-- A Gemini Live session used for video diagnosis. The 2-minute audio+video
-- cap without compression is why compression and resumption are recorded.
CREATE TABLE diagnosis_session (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  centre_id        uuid NOT NULL DEFAULT current_centre() REFERENCES service_centre(id),
  ticket_id        uuid NOT NULL REFERENCES ticket(id) ON DELETE CASCADE,
  conversation_id  uuid REFERENCES conversation(id),
  provider         text NOT NULL DEFAULT 'gemini_live',
  model            text,
  link_route       text NOT NULL CHECK (link_route IN ('in_app','whatsapp_link','sms_link','same_session')),
  started_at       timestamptz NOT NULL,
  ended_at         timestamptz,
  duration_s       integer CHECK (duration_s >= 0),
  video_on         boolean NOT NULL DEFAULT true,
  compression_on   boolean NOT NULL DEFAULT true,
  resumptions      smallint NOT NULL DEFAULT 0 CHECK (resumptions >= 0),
  frames_consent   boolean NOT NULL DEFAULT false,
  end_reason       text CHECK (end_reason IN ('completed','household_stopped','safety_stop','timeout','connection_lost')),
  observations     jsonb NOT NULL DEFAULT '[]'      -- what the agent saw: [{t_s, note}]
);

CREATE TABLE diagnosis_media (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  centre_id        uuid NOT NULL DEFAULT current_centre() REFERENCES service_centre(id),
  session_id       uuid NOT NULL REFERENCES diagnosis_session(id) ON DELETE CASCADE,
  kind             text NOT NULL CHECK (kind IN ('frame','clip','audio')),
  storage_uri      text NOT NULL,
  retain_until     date NOT NULL,
  created_at       timestamptz NOT NULL DEFAULT now()
);

-- What was tried. One row per safe fix offered after gate 1 was a yes.
CREATE TABLE fix_attempt (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  centre_id        uuid NOT NULL DEFAULT current_centre() REFERENCES service_centre(id),
  ticket_id        uuid NOT NULL REFERENCES ticket(id) ON DELETE CASCADE,
  catalogue_id     uuid NOT NULL REFERENCES safe_fix_catalogue(id),
  conversation_id  uuid REFERENCES conversation(id),
  session_id       uuid REFERENCES diagnosis_session(id),
  offered_at       timestamptz NOT NULL,
  started_at       timestamptz,
  ended_at         timestamptz,
  steps_done       smallint NOT NULL DEFAULT 0 CHECK (steps_done >= 0),
  outcome          text NOT NULL CHECK (outcome IN ('worked','not_worked','abandoned','safety_stop')),
  household_report text,
  observed_on_video boolean NOT NULL DEFAULT false
);

CREATE TABLE appliance_event (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  appliance_id  uuid NOT NULL REFERENCES appliance(id) ON DELETE RESTRICT,
  centre_id     uuid REFERENCES service_centre(id),     -- centre that recorded it; null for platform events
  event_type    text NOT NULL CHECK (event_type IN (
                  'purchase','install','service','repair','part_replaced','self_fix',
                  'advice_given','reminder_sent','index_change','warranty_change','merge','note')),
  visibility    text NOT NULL DEFAULT 'technical' CHECK (visibility IN ('technical','private')),
  occurred_at   timestamptz NOT NULL DEFAULT now(),
  ticket_id     uuid REFERENCES ticket(id),
  details       jsonb NOT NULL DEFAULT '{}'              -- technical details only; no prices or notes on the centre
);

CREATE TABLE visit_plan (
  id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  centre_id             uuid NOT NULL DEFAULT current_centre() REFERENCES service_centre(id),
  ticket_id             uuid NOT NULL REFERENCES ticket(id) ON DELETE CASCADE,
  version               integer NOT NULL DEFAULT 1,
  trigger_reason        text NOT NULL DEFAULT 'initial' CHECK (trigger_reason IN ('initial','self_fix_failed','new_info','reclassified','brand_info')),
  already_tried         jsonb NOT NULL DEFAULT '[]',      -- fix attempts and checks done before this plan
  required_skills       jsonb NOT NULL DEFAULT '[]',
  est_duration_p50_min  integer CHECK (est_duration_p50_min > 0),
  est_duration_p80_min  integer CHECK (est_duration_p80_min > 0),
  tools_needed          text[] NOT NULL DEFAULT '{}',
  requires_safety_cert  text[] NOT NULL DEFAULT '{}',
  access_notes          text,
  confidence            numeric(3,2) CHECK (confidence BETWEEN 0 AND 1),
  model_version         text,
  created_at            timestamptz NOT NULL DEFAULT now(),
  UNIQUE (ticket_id, version),
  CHECK (est_duration_p80_min IS NULL OR est_duration_p50_min IS NULL OR est_duration_p80_min >= est_duration_p50_min)
);

CREATE TABLE plan_hypothesis (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  centre_id      uuid NOT NULL DEFAULT current_centre() REFERENCES service_centre(id),
  visit_plan_id  uuid NOT NULL REFERENCES visit_plan(id) ON DELETE CASCADE,
  rank           smallint NOT NULL CHECK (rank > 0),
  cause          text NOT NULL,
  probability    numeric(4,3) NOT NULL CHECK (probability BETWEEN 0 AND 1),
  evidence       jsonb NOT NULL DEFAULT '[]',
  UNIQUE (visit_plan_id, rank)
);

CREATE TABLE plan_part (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  centre_id      uuid NOT NULL DEFAULT current_centre() REFERENCES service_centre(id),
  visit_plan_id  uuid NOT NULL REFERENCES visit_plan(id) ON DELETE CASCADE,
  part_id        uuid NOT NULL REFERENCES part_catalogue(id),
  probability    numeric(4,3) NOT NULL CHECK (probability BETWEEN 0 AND 1),
  quantity       smallint NOT NULL DEFAULT 1 CHECK (quantity > 0),
  UNIQUE (visit_plan_id, part_id)
);

-- The agent's ranked technician candidates inside the centre. The centre
-- can reassign from its console; the override and its reason are logged
-- and used as a training signal.
CREATE TABLE assignment_candidate (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  centre_id        uuid NOT NULL DEFAULT current_centre() REFERENCES service_centre(id),
  ticket_id        uuid NOT NULL REFERENCES ticket(id) ON DELETE CASCADE,
  visit_plan_id    uuid NOT NULL REFERENCES visit_plan(id),
  technician_id    uuid NOT NULL REFERENCES technician(id),
  slot_start       timestamptz NOT NULL,
  slot_end         timestamptz NOT NULL,
  rank             smallint NOT NULL CHECK (rank > 0),
  score            numeric(6,3),
  score_breakdown  jsonb NOT NULL DEFAULT '{}',
  config_id        uuid REFERENCES scoring_config(id),
  outcome          text NOT NULL DEFAULT 'proposed' CHECK (outcome IN ('proposed','chosen','not_chosen')),
  chosen_by        text CHECK (chosen_by IN ('agent','centre_console')),
  override_reason  text,
  created_at       timestamptz NOT NULL DEFAULT now(),
  CHECK (slot_end > slot_start),
  CHECK (chosen_by <> 'centre_console' OR override_reason IS NOT NULL OR outcome <> 'chosen')
);

-- The slots put to the household for one technician and window.
CREATE TABLE slot_proposal (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  centre_id         uuid NOT NULL DEFAULT current_centre() REFERENCES service_centre(id),
  ticket_id         uuid NOT NULL REFERENCES ticket(id) ON DELETE CASCADE,
  candidate_id      uuid REFERENCES assignment_candidate(id),
  slot_start        timestamptz NOT NULL,
  slot_end          timestamptz NOT NULL,
  price_low_paise   bigint CHECK (price_low_paise >= 0),
  price_high_paise  bigint CHECK (price_high_paise >= price_low_paise),
  shown_at          timestamptz,
  accepted          boolean,
  accepted_at       timestamptz,
  expires_at        timestamptz,
  CHECK (slot_end > slot_start)
);

CREATE TABLE quote (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  centre_id        uuid NOT NULL DEFAULT current_centre() REFERENCES service_centre(id),
  ticket_id        uuid NOT NULL REFERENCES ticket(id) ON DELETE CASCADE,
  version          integer NOT NULL DEFAULT 1,
  quote_type       text NOT NULL CHECK (quote_type IN ('estimate','firm')),
  valid_until      timestamptz,
  approved_at      timestamptz,
  approval_channel text CHECK (approval_channel IN ('whatsapp','app','in_person','voice')),
  approval_ref     text,
  created_at       timestamptz NOT NULL DEFAULT now(),
  UNIQUE (ticket_id, version)
);

CREATE TABLE quote_line (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  centre_id     uuid NOT NULL DEFAULT current_centre() REFERENCES service_centre(id),
  quote_id      uuid NOT NULL REFERENCES quote(id) ON DELETE CASCADE,
  line_type     text NOT NULL CHECK (line_type IN ('visit_fee','labour','part','travel','discount','tax')),
  description   text NOT NULL,
  part_id       uuid REFERENCES part_catalogue(id),
  quantity      numeric(8,2) NOT NULL DEFAULT 1 CHECK (quantity > 0),
  amount_paise  bigint NOT NULL,
  payer         text NOT NULL CHECK (payer IN ('brand_warranty','extended_warranty','amc','household','keepwell')),
  plan_id       uuid REFERENCES coverage_plan(id),
  CHECK (line_type <> 'part' OR part_id IS NOT NULL)
);

CREATE TABLE visit (
  id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  centre_id             uuid NOT NULL DEFAULT current_centre() REFERENCES service_centre(id),
  ticket_id             uuid NOT NULL REFERENCES ticket(id),
  technician_id         uuid NOT NULL REFERENCES technician(id),
  planned_start         timestamptz NOT NULL,
  planned_end           timestamptz NOT NULL,
  is_return_visit       boolean NOT NULL DEFAULT false,
  parent_visit_id       uuid REFERENCES visit(id),
  check_in_at           timestamptz,
  check_in_location     geography(Point,4326),            -- @geo
  check_out_at          timestamptz,
  checklist             jsonb NOT NULL DEFAULT '[]',
  outcome               text CHECK (outcome IN ('fixed','partial','needs_part','not_repairable','no_access')),
  outcome_notes         text,
  root_cause_confirmed  text,
  closure_otp_ref       text,
  closure_confirmed_at  timestamptz,
  rating                smallint CHECK (rating BETWEEN 1 AND 5),
  created_at            timestamptz NOT NULL DEFAULT now(),
  updated_at            timestamptz NOT NULL DEFAULT now(),
  CHECK (planned_end > planned_start),
  CHECK (closure_confirmed_at IS NULL OR closure_otp_ref IS NOT NULL)
);

CREATE TABLE visit_media (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  centre_id    uuid NOT NULL DEFAULT current_centre() REFERENCES service_centre(id),
  visit_id     uuid NOT NULL REFERENCES visit(id) ON DELETE CASCADE,
  kind         text NOT NULL CHECK (kind IN ('before','after','part','voice_note','invoice')),
  storage_uri  text NOT NULL,
  created_at   timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE visit_part_used (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  centre_id    uuid NOT NULL DEFAULT current_centre() REFERENCES service_centre(id),
  visit_id     uuid NOT NULL REFERENCES visit(id) ON DELETE CASCADE,
  part_id      uuid NOT NULL REFERENCES part_catalogue(id),
  serial_no    text,
  quantity     smallint NOT NULL DEFAULT 1 CHECK (quantity > 0),
  source_type  text CHECK (source_type IN ('van','centre','parts_centre','courier','household'))
);

CREATE TABLE reservation (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  centre_id    uuid NOT NULL DEFAULT current_centre() REFERENCES service_centre(id),
  part_id      uuid NOT NULL REFERENCES part_catalogue(id),
  quantity     smallint NOT NULL DEFAULT 1 CHECK (quantity > 0),
  holder_type  text NOT NULL CHECK (holder_type IN ('van','centre','parts_centre')),
  holder_id    uuid NOT NULL,
  visit_id     uuid NOT NULL REFERENCES visit(id) ON DELETE CASCADE,
  ready_by     timestamptz NOT NULL,
  status       text NOT NULL DEFAULT 'requested' CHECK (status IN ('requested','confirmed','collected','released','expired')),
  created_at   timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE route (
  id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  centre_id            uuid NOT NULL DEFAULT current_centre() REFERENCES service_centre(id),
  technician_id        uuid NOT NULL REFERENCES technician(id),
  route_date           date NOT NULL,
  batched              boolean NOT NULL DEFAULT false,
  optimiser            text NOT NULL DEFAULT 'manual' CHECK (optimiser IN ('manual','or_tools','route_optimization_api')),
  planned_travel_min   integer CHECK (planned_travel_min >= 0),
  actual_travel_min    integer CHECK (actual_travel_min >= 0),
  created_at           timestamptz NOT NULL DEFAULT now(),
  UNIQUE (technician_id, route_date)
);

CREATE TABLE route_stop (
  route_id         uuid NOT NULL REFERENCES route(id) ON DELETE CASCADE,
  centre_id        uuid NOT NULL DEFAULT current_centre() REFERENCES service_centre(id),
  seq              smallint NOT NULL CHECK (seq > 0),
  visit_id         uuid NOT NULL UNIQUE REFERENCES visit(id),
  planned_arrival  timestamptz,
  actual_arrival   timestamptz,
  PRIMARY KEY (route_id, seq)
);

CREATE TABLE settlement_line (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  centre_id     uuid NOT NULL DEFAULT current_centre() REFERENCES service_centre(id),
  ticket_id     uuid NOT NULL REFERENCES ticket(id),
  party_type    text NOT NULL CHECK (party_type IN ('household','brand','plan_provider','centre','parts_centre','keepwell')),
  party_id      uuid,
  direction     text NOT NULL CHECK (direction IN ('receivable','payable')),
  amount_paise  bigint NOT NULL CHECK (amount_paise >= 0),
  status        text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','paid','failed','waived')),
  payment_ref   text,
  due_at        timestamptz,
  settled_at    timestamptz
);

CREATE TABLE feedback (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  centre_id     uuid NOT NULL DEFAULT current_centre() REFERENCES service_centre(id),
  ticket_id     uuid NOT NULL REFERENCES ticket(id),
  visit_id      uuid REFERENCES visit(id),
  from_type     text NOT NULL CHECK (from_type IN ('household','technician','centre')),
  rating        smallint CHECK (rating BETWEEN 1 AND 5),
  reason_codes  text[] NOT NULL DEFAULT '{}',
  comment       text,
  is_dispute    boolean NOT NULL DEFAULT false,
  resolution    text,
  created_at    timestamptz NOT NULL DEFAULT now()
);

-- Reminders are sent only by the centre that last served the appliance, and
-- only with the household's consent for that purpose.
CREATE TABLE reminder (
  id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  centre_id          uuid NOT NULL DEFAULT current_centre() REFERENCES service_centre(id),
  household_id       uuid NOT NULL REFERENCES household(id) ON DELETE CASCADE,
  appliance_id       uuid REFERENCES appliance(id) ON DELETE CASCADE,
  reminder_type      text NOT NULL CHECK (reminder_type IN (
                       'service_due','seasonal','warranty_ending','plan_renewal',
                       'consumable','after_repair','rating_request')),
  due_on             date NOT NULL,
  template_name      text,
  whatsapp_category  text CHECK (whatsapp_category IN ('utility','marketing','authentication','service')),
  status             text NOT NULL DEFAULT 'scheduled' CHECK (status IN (
                       'scheduled','sent','delivered','read','acted','snoozed','suppressed','failed')),
  scheduled_at       timestamptz,
  sent_at            timestamptz,
  delivered_at       timestamptz,
  read_at            timestamptz,
  action_taken       text,
  ticket_id          uuid REFERENCES ticket(id),
  created_at         timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE ticket ADD CONSTRAINT ticket_origin_reminder_fk FOREIGN KEY (origin_reminder_id) REFERENCES reminder(id);

-- ---------------------------------------------------------------------
-- 6. Experience layer (L3): anonymised closed jobs with embeddings.
--    Shared across centres; no household, address or centre link.
-- ---------------------------------------------------------------------
CREATE TABLE experience_case (
  id                       uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source_visit_id          uuid UNIQUE REFERENCES visit(id) ON DELETE SET NULL,
  brand_id                 uuid NOT NULL REFERENCES brand(id),
  category_code            text NOT NULL REFERENCES appliance_category(code),
  model_series             text,
  pincode                  text,
  symptom_text             text NOT NULL,
  error_code               text,
  self_fix_tried           text[] NOT NULL DEFAULT '{}',   -- safe_fix_catalogue codes tried before the visit
  root_cause               text NOT NULL,
  parts                    jsonb NOT NULL DEFAULT '[]',
  duration_min             integer CHECK (duration_min > 0),
  cost_paise               bigint CHECK (cost_paise >= 0),
  outcome                  text NOT NULL,
  verified_by_technician   boolean NOT NULL DEFAULT false,
  embedding                vector(768),                   -- @vec
  created_at               timestamptz NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------
-- 7. Consent and audit
-- ---------------------------------------------------------------------
CREATE TABLE consent_ledger (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  subject_type    text NOT NULL CHECK (subject_type IN ('household','member','technician','centre')),
  subject_id      uuid NOT NULL,
  purpose         text NOT NULL CHECK (purpose IN (
                    'memory','service_reminders','warranty_alerts','follow_up',
                    'share_technical_history','photos_voice','video_diagnosis',
                    'frame_retention','analytics')),
  scope_centre_id uuid REFERENCES service_centre(id),   -- set for centre-specific purposes such as reminders
  notice_version  text NOT NULL,
  granted_at      timestamptz NOT NULL DEFAULT now(),
  channel         text NOT NULL,
  withdrawn_at    timestamptz,
  evidence        jsonb NOT NULL DEFAULT '{}',
  CHECK (withdrawn_at IS NULL OR withdrawn_at >= granted_at)
);

CREATE TABLE access_log (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  actor_type       text NOT NULL CHECK (actor_type IN ('technician','centre_user','keepwell_admin','agent','system')),
  actor_id         text NOT NULL,
  actor_centre_id  uuid REFERENCES service_centre(id),
  record_table     text NOT NULL,
  record_id        uuid NOT NULL,
  owner_centre_id  uuid REFERENCES service_centre(id),    -- centre that recorded the data read
  cross_centre     boolean NOT NULL DEFAULT false,
  ticket_id        uuid REFERENCES ticket(id),
  reason           text NOT NULL,
  occurred_at      timestamptz NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------
-- 8. Late foreign keys
-- ---------------------------------------------------------------------
ALTER TABLE technician_availability
  ADD CONSTRAINT technician_availability_visit_fk
  FOREIGN KEY (visit_id) REFERENCES visit(id) ON DELETE SET NULL;

-- ---------------------------------------------------------------------
-- 9. Triggers
-- ---------------------------------------------------------------------
DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY[
    'kb_document','service_centre','technician','parts_centre','household',
    'appliance','ticket','visit'
  ] LOOP
    EXECUTE format(
      'CREATE TRIGGER %I BEFORE UPDATE ON %I FOR EACH ROW EXECUTE FUNCTION touch_updated_at()',
      t || '_touch', t);
  END LOOP;
END $$;

CREATE TRIGGER appliance_event_append_only BEFORE UPDATE OR DELETE ON appliance_event
  FOR EACH ROW EXECUTE FUNCTION deny_mutation();
CREATE TRIGGER access_log_append_only BEFORE UPDATE OR DELETE ON access_log
  FOR EACH ROW EXECUTE FUNCTION deny_mutation();
CREATE TRIGGER identity_merge_no_delete BEFORE DELETE ON identity_merge
  FOR EACH ROW EXECUTE FUNCTION deny_mutation();

-- ---------------------------------------------------------------------
-- 10. Indexes
-- ---------------------------------------------------------------------
CREATE INDEX service_centre_loc_gix       ON service_centre USING gist (location);        -- @geo
CREATE INDEX technician_anchor_gix        ON technician USING gist (route_anchor);        -- @geo
CREATE INDEX parts_centre_loc_gix         ON parts_centre USING gist (location);          -- @geo
CREATE INDEX household_loc_gix            ON household USING gist (location);             -- @geo
CREATE INDEX ticket_visit_loc_gix         ON ticket USING gist (visit_location);          -- @geo
CREATE INDEX experience_case_emb_hnsw     ON experience_case USING hnsw (embedding vector_cosine_ops);  -- @vec

CREATE INDEX service_centre_pincodes_gin  ON service_centre USING gin (service_pincodes);
CREATE INDEX centre_auth_lookup_idx       ON centre_brand_authorisation (brand_id, centre_id, valid_from, valid_to);
CREATE INDEX technician_centre_idx        ON technician (centre_id) WHERE active;
CREATE INDEX technician_skill_lookup_idx  ON technician_skill (category_code, brand_id, fault_class, level);
CREATE INDEX availability_open_idx        ON technician_availability (slot_start, technician_id) WHERE status = 'open';
CREATE INDEX stock_part_idx               ON stock (part_id, holder_type);
CREATE INDEX part_compat_model_idx        ON part_compatibility (model_id);
CREATE INDEX safe_fix_lookup_idx          ON safe_fix_catalogue (category_code, brand_id, fault_family) WHERE status = 'active';

CREATE INDEX household_member_hh_idx      ON household_member (household_id);
CREATE INDEX household_link_centre_idx    ON household_centre_link (centre_id, last_served_at DESC);
CREATE INDEX appliance_household_idx      ON appliance (household_id) WHERE status = 'active';
CREATE INDEX appliance_due_idx            ON appliance (last_served_centre_id, next_due_at) WHERE status = 'active';
CREATE INDEX appliance_event_idx          ON appliance_event (appliance_id, occurred_at DESC);

CREATE INDEX ticket_centre_status_idx     ON ticket (centre_id, status) WHERE status NOT IN ('closed','cancelled');
CREATE INDEX ticket_household_idx         ON ticket (household_id, created_at DESC);
CREATE INDEX ticket_urgency_idx           ON ticket (centre_id, urgency_class, first_visit_by) WHERE status NOT IN ('closed','cancelled');
CREATE INDEX conversation_ticket_idx      ON conversation (ticket_id, started_at);
CREATE INDEX fix_attempt_ticket_idx       ON fix_attempt (ticket_id, offered_at);
CREATE INDEX fix_attempt_catalogue_idx    ON fix_attempt (catalogue_id, outcome);
CREATE INDEX assignment_ticket_idx        ON assignment_candidate (ticket_id, rank);
CREATE INDEX visit_ticket_idx             ON visit (ticket_id, planned_start);
CREATE INDEX visit_technician_idx         ON visit (technician_id, planned_start);
CREATE INDEX reservation_visit_idx        ON reservation (visit_id);
CREATE INDEX settlement_ticket_idx        ON settlement_line (ticket_id);
CREATE INDEX reminder_due_idx             ON reminder (centre_id, due_on) WHERE status = 'scheduled';
CREATE INDEX experience_case_filter_idx   ON experience_case (brand_id, category_code, model_series);
CREATE INDEX consent_lookup_idx           ON consent_ledger (subject_type, subject_id, purpose, granted_at DESC);
CREATE INDEX access_log_record_idx        ON access_log (record_table, record_id, occurred_at DESC);
CREATE INDEX access_log_cross_idx         ON access_log (actor_centre_id, occurred_at DESC) WHERE cross_centre;

-- ---------------------------------------------------------------------
-- 11. Views
-- ---------------------------------------------------------------------
CREATE VIEW current_consent AS
SELECT DISTINCT ON (subject_type, subject_id, purpose, scope_centre_id)
       subject_type, subject_id, purpose, scope_centre_id, notice_version, granted_at, channel
FROM consent_ledger
WHERE withdrawn_at IS NULL
ORDER BY subject_type, subject_id, purpose, scope_centre_id, granted_at DESC;

CREATE VIEW quote_total AS
SELECT q.id AS quote_id, q.ticket_id, q.centre_id, q.version, q.quote_type,
       SUM(l.amount_paise)                                          AS total_paise,
       SUM(l.amount_paise) FILTER (WHERE l.payer = 'household')     AS household_paise,
       SUM(l.amount_paise) FILTER (WHERE l.payer <> 'household')    AS covered_paise
FROM quote q
JOIN quote_line l ON l.quote_id = q.id
GROUP BY q.id;

CREATE VIEW quote_variance AS
WITH est AS (
  SELECT DISTINCT ON (ticket_id) ticket_id, total_paise
  FROM quote_total WHERE quote_type = 'estimate' ORDER BY ticket_id, version
), fin AS (
  SELECT DISTINCT ON (ticket_id) ticket_id, total_paise
  FROM quote_total WHERE quote_type = 'firm' ORDER BY ticket_id, version DESC
)
SELECT fin.ticket_id, est.total_paise AS estimate_paise, fin.total_paise AS final_paise,
       CASE WHEN est.total_paise > 0
            THEN round(100.0 * (fin.total_paise - est.total_paise) / est.total_paise, 2) END AS variance_pct
FROM fin JOIN est USING (ticket_id);

-- First-time fix: the first visit ended 'fixed' and the ticket had no other visit.
-- Tickets resolved by a self-fix have no visit and do not appear here.
CREATE VIEW first_visit_outcome AS
WITH ranked AS (
  SELECT v.*, row_number() OVER (PARTITION BY v.ticket_id ORDER BY v.planned_start) AS rn,
         count(*) OVER (PARTITION BY v.ticket_id) AS visits_on_ticket
  FROM visit v
)
SELECT r.ticket_id, r.id AS visit_id, r.technician_id, r.centre_id,
       a.category_code, a.brand_id, r.planned_start,
       (r.outcome = 'fixed' AND r.visits_on_ticket = 1) AS fixed_first_time
FROM ranked r
JOIN ticket t ON t.id = r.ticket_id
JOIN appliance a ON a.id = t.appliance_id
WHERE r.rn = 1 AND r.outcome IS NOT NULL AND t.job_type = 'repair';

-- Due within 30 days, with the centre that would send the reminder.
CREATE VIEW appliance_due AS
SELECT a.id AS appliance_id, a.household_id, a.category_code, a.brand_id,
       a.last_served_centre_id AS centre_id, a.next_due_at, a.care_index
FROM appliance a
WHERE a.status = 'active' AND a.last_served_centre_id IS NOT NULL
  AND a.next_due_at <= current_date + 30;

-- What was tried on a ticket, in order. Feeds the visit plan and the technician brief.
CREATE VIEW tried_summary AS
SELECT f.ticket_id, f.centre_id,
       jsonb_agg(jsonb_build_object(
         'fix', c.code, 'title', c.title, 'steps_done', f.steps_done, 'of', c.step_count,
         'outcome', f.outcome, 'household_said', f.household_report, 'seen_on_video', f.observed_on_video)
         ORDER BY f.offered_at) AS tried
FROM fix_attempt f JOIN safe_fix_catalogue c ON c.id = f.catalogue_id
GROUP BY f.ticket_id, f.centre_id;

-- How often each safe fix works. Drives review of the catalogue.
CREATE VIEW safe_fix_effectiveness AS
SELECT c.code, c.category_code, c.fault_family,
       count(*)                                         AS attempts,
       count(*) FILTER (WHERE f.outcome = 'worked')     AS worked,
       count(*) FILTER (WHERE f.outcome = 'safety_stop') AS safety_stops,
       round(avg((f.outcome = 'worked')::int), 3)       AS worked_rate
FROM fix_attempt f JOIN safe_fix_catalogue c ON c.id = f.catalogue_id
GROUP BY c.code, c.category_code, c.fault_family;

-- ---------------------------------------------------------------------
-- 12. Cross-centre functions. These are the only paths across centres.
-- ---------------------------------------------------------------------
-- Highest authorisation a centre holds for a brand on a date, or 'none'.
CREATE FUNCTION centre_authority(p_centre uuid, p_brand uuid, p_on date DEFAULT current_date)
RETURNS text LANGUAGE sql STABLE AS $$
  SELECT coalesce((
    SELECT level FROM centre_brand_authorisation
    WHERE centre_id = p_centre AND brand_id = p_brand
      AND valid_from <= p_on AND (valid_to IS NULL OR valid_to > p_on)
    ORDER BY CASE level WHEN 'authorised_service' THEN 1 WHEN 'installation_only' THEN 2 ELSE 3 END
    LIMIT 1), 'none')
$$;

-- Find or create a household from a phone hash on a centre's line, and
-- link it to that centre. If the household already existed with other
-- centres, the call is logged as a cross-centre lookup. Returns the global id.
CREATE FUNCTION identify_household(p_phone_hash bytea, p_phone_enc bytea, p_centre uuid, p_via text DEFAULT 'call_line')
RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER SET search_path = kw, public AS $$
DECLARE h uuid; existed boolean;
BEGIN
  SELECT id INTO h FROM household WHERE phone_hash = p_phone_hash AND status <> 'merged';
  existed := h IS NOT NULL;
  IF NOT existed THEN
    INSERT INTO household (phone_enc, phone_hash, phone_verified_at, verified_via)
    VALUES (p_phone_enc, p_phone_hash, now(), p_via) RETURNING id INTO h;
  END IF;
  INSERT INTO household_centre_link (household_id, centre_id, first_contact_at)
  VALUES (h, p_centre, now())
  ON CONFLICT (household_id, centre_id) DO UPDATE SET contact_count = household_centre_link.contact_count + 1;
  IF existed AND NOT EXISTS (SELECT 1 FROM household_centre_link WHERE household_id = h AND centre_id <> p_centre) THEN
    NULL;  -- known to Keepwell only through this centre; nothing crossed
  ELSIF existed THEN
    INSERT INTO access_log (actor_type, actor_id, actor_centre_id, record_table, record_id, cross_centre, reason)
    VALUES ('agent', 'identify_household', p_centre, 'household', h, true, 'identity lookup on first contact with this centre');
  END IF;
  RETURN h;
END $$;

-- Does the household that owns this appliance allow technical history to be shared?
CREATE FUNCTION shared_history_allowed(p_appliance uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = kw, public AS $$
  SELECT EXISTS (
    SELECT 1 FROM appliance a
    JOIN current_consent c ON c.subject_type = 'household' AND c.subject_id = a.household_id
                          AND c.purpose = 'share_technical_history'
    WHERE a.id = p_appliance)
$$;

-- Technical history of an appliance for a centre that did not record it.
-- Own rows are always returned. Rows from other centres are returned only
-- when the household has consented; each such read is logged.
CREATE FUNCTION read_shared_history(p_appliance uuid, p_centre uuid, p_ticket uuid, p_reason text)
RETURNS SETOF appliance_event LANGUAGE plpgsql SECURITY DEFINER SET search_path = kw, public AS $$
DECLARE ok boolean := shared_history_allowed(p_appliance);
BEGIN
  IF NOT EXISTS (SELECT 1 FROM household_centre_link l JOIN appliance a ON a.household_id = l.household_id
                 WHERE a.id = p_appliance AND l.centre_id = p_centre) THEN
    RAISE EXCEPTION 'centre % has no link to this household', p_centre;
  END IF;
  IF ok THEN
    INSERT INTO access_log (actor_type, actor_id, actor_centre_id, record_table, record_id, owner_centre_id, cross_centre, ticket_id, reason)
    SELECT 'agent', 'read_shared_history', p_centre, 'appliance_event', e.id, e.centre_id, true, p_ticket, p_reason
    FROM appliance_event e
    WHERE e.appliance_id = p_appliance AND e.visibility = 'technical' AND e.centre_id IS DISTINCT FROM p_centre;
  END IF;
  RETURN QUERY
    SELECT * FROM appliance_event e
    WHERE e.appliance_id = p_appliance
      AND (e.centre_id = p_centre OR (ok AND e.visibility = 'technical'))
    ORDER BY e.occurred_at;
END $$;

-- ---------------------------------------------------------------------
-- 13. Row-level security
-- ---------------------------------------------------------------------
-- Centre-owned tables: a centre sees its own rows; platform jobs see all.
DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY[
    'ticket','conversation','urgency_assessment','consent_gate','clarifying_qa','diagnosis_session',
    'diagnosis_media','fix_attempt','visit_plan','plan_hypothesis','plan_part','assignment_candidate',
    'slot_proposal','quote','quote_line','visit','visit_media','visit_part_used','reservation','route',
    'route_stop','settlement_line','feedback','reminder','brand_referral','retailer_handover',
    'centre_price','technician','technician_skill','technician_availability','technician_metrics'
  ] LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
    EXECUTE format('CREATE POLICY centre_isolation ON %I USING (centre_id = current_centre() OR is_platform()) WITH CHECK (centre_id = current_centre() OR is_platform())', t);
  END LOOP;
END $$;

ALTER TABLE centre_commercial ENABLE ROW LEVEL SECURITY;
CREATE POLICY centre_isolation ON centre_commercial USING (centre_id = current_centre() OR is_platform()) WITH CHECK (centre_id = current_centre() OR is_platform());

-- Stock: own van and centre stock, plus the shared parts network.
ALTER TABLE stock ENABLE ROW LEVEL SECURITY;
CREATE POLICY stock_visibility ON stock USING (centre_id IS NULL OR centre_id = current_centre() OR is_platform())
  WITH CHECK (centre_id = current_centre() OR is_platform());

-- Households and appliances: visible to a centre only through household_centre_link.
CREATE FUNCTION centre_knows_household(p_household uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = kw, public AS $$
  SELECT is_platform() OR EXISTS (SELECT 1 FROM household_centre_link WHERE household_id = p_household AND centre_id = current_centre())
$$;

ALTER TABLE household ENABLE ROW LEVEL SECURITY;
CREATE POLICY via_link ON household USING (centre_knows_household(id));
ALTER TABLE household_member ENABLE ROW LEVEL SECURITY;
CREATE POLICY via_link ON household_member USING (centre_knows_household(household_id));
ALTER TABLE appliance ENABLE ROW LEVEL SECURITY;
CREATE POLICY via_link ON appliance USING (centre_knows_household(household_id));
ALTER TABLE household_centre_link ENABLE ROW LEVEL SECURITY;
CREATE POLICY own_links ON household_centre_link USING (centre_id = current_centre() OR is_platform());

-- Event history: a centre reads what it recorded. Other centres' technical
-- events come only through read_shared_history().
ALTER TABLE appliance_event ENABLE ROW LEVEL SECURITY;
CREATE POLICY own_events ON appliance_event USING (centre_id = current_centre() OR centre_id IS NULL AND centre_knows_household((SELECT household_id FROM appliance WHERE id = appliance_id)) OR is_platform())
  WITH CHECK (centre_id = current_centre() OR is_platform());

ALTER TABLE access_log ENABLE ROW LEVEL SECURITY;
CREATE POLICY own_reads ON access_log USING (actor_centre_id = current_centre() OR owner_centre_id = current_centre() OR is_platform());
CREATE POLICY log_insert ON access_log FOR INSERT WITH CHECK (true);

ALTER TABLE consent_ledger ENABLE ROW LEVEL SECURITY;
CREATE POLICY consent_via_link ON consent_ledger
  USING (is_platform() OR (subject_type = 'household' AND centre_knows_household(subject_id))
         OR (subject_type = 'member' AND centre_knows_household((SELECT household_id FROM household_member WHERE id = subject_id))))
  WITH CHECK (true);

GRANT USAGE ON SCHEMA kw TO kw_app;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA kw TO kw_app;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA kw TO kw_app;
REVOKE UPDATE, DELETE ON appliance_event, access_log FROM kw_app;

COMMIT;
