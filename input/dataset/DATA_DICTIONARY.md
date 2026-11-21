# Data dictionary (schema v0.2)

Generated from `keepwell_schema.sql`. Money is in paise. Times are timestamptz (IST in the CSVs). Geography columns are loaded from EWKT (`SRID=4326;POINT(lon lat)`). Tables marked **centre-owned** carry `centre_id` and are isolated by row-level security. Tables marked **app output** are empty in the seed because the app writes them.

## 1. Reference data: catalogue (L1), policy and price (L4), safe fixes (L6)

### brand

| Column | Type | Constraints and values | Note |
|---|---|---|---|
| id | uuid | PK |  |
| name | text | required; unique |  |
| forwarding_enabled | boolean | required; default false | brand can forward requests to a centre |
| created_at | timestamptz | required |  |

### appliance_category

| Column | Type | Constraints and values | Note |
|---|---|---|---|
| code | text | PK |  |
| name | text | required |  |

### category_norm

| Column | Type | Constraints and values | Note |
|---|---|---|---|
| id | uuid | PK |  |
| category_code | text | required; → appliance_category |  |
| service_interval_months | smallint | required |  |
| typical_life_years | smallint | required |  |
| valid_from | date | required |  |
| valid_to | date |  |  |

Table rules:
- `CHECK (valid_to IS NULL OR valid_to > valid_from)`
- `EXCLUDE USING gist (category_code WITH =, daterange(valid_from, valid_to) WITH &&)`

### appliance_model

| Column | Type | Constraints and values | Note |
|---|---|---|---|
| id | uuid | PK |  |
| brand_id | uuid | required; → brand |  |
| category_code | text | required; → appliance_category |  |
| model_code | text | required |  |
| series | text |  |  |
| year_from | smallint |  |  |
| specs | jsonb | required; default '{}' |  |
| created_at | timestamptz | required |  |

Table rules:
- `UNIQUE (brand_id, model_code)`

### rate_card

Platform reference visit fee and labour (benchmark). Each centre's own prices are in centre_price and are private to that centre.

| Column | Type | Constraints and values | Note |
|---|---|---|---|
| id | uuid | PK |  |
| category_code | text | required; → appliance_category |  |
| job_type | text | required; values: installation / preventive_service / repair / coverage_claim / uninstall_reinstall / inspection_advice |  |
| complexity_band | text | required; values: basic / standard / complex |  |
| visit_fee_paise | bigint | required |  |
| labour_paise | bigint | required |  |
| valid_from | date | required |  |
| valid_to | date |  |  |

Table rules:
- `CHECK (valid_to IS NULL OR valid_to > valid_from)`
- `UNIQUE (category_code, job_type, complexity_band, valid_from)`

### kb_document

| Column | Type | Constraints and values | Note |
|---|---|---|---|
| id | uuid | PK |  |
| title | text | required |  |
| brand_id | uuid | → brand |  |
| category_code | text | → appliance_category |  |
| model_series | text |  |  |
| doc_type | text | required; values: manual / error_codes / troubleshooting / installation / bulletin / parts_view / warranty_terms / amc_terms / safe_fix |  |
| language | text | required; default 'en' |  |
| version_year | smallint |  |  |
| valid_to | date |  |  |
| authority | text | required; values: oem / centre_verified / keepwell |  |
| audience | text | required; values: technician / household / both; default 'technician' |  |
| storage_uri | text | required |  |
| file_search_store | text |  |  |
| file_search_doc | text |  |  |
| rights_status | text | required; values: confirmed / pending / none; default 'pending' |  |
| created_at | timestamptz | required |  |
| updated_at | timestamptz | required |  |

### coverage_plan

| Column | Type | Constraints and values | Note |
|---|---|---|---|
| id | uuid | PK |  |
| kind | text | required; values: brand_warranty / extended_warranty / amc |  |
| provider_name | text | required |  |
| brand_id | uuid | → brand |  |
| terms_doc_id | uuid | → kb_document |  |
| covers | jsonb | required; default '{}' |  |
| created_at | timestamptz | required |  |

### safe_fix_catalogue

Layer 6. A fix the agent may guide a household through. The CHECK constraints are the safe-fix threshold from the design document: a fix that breaks them cannot be stored as active.

| Column | Type | Constraints and values | Note |
|---|---|---|---|
| id | uuid | PK |  |
| code | text | required; unique |  |
| category_code | text | required; → appliance_category |  |
| brand_id | uuid | → brand | null = any brand |
| model_series | text |  | null = any series |
| fault_family | text | required |  |
| title | text | required |  |
| symptom_terms | text[] | required; default '{}' |  |
| steps | jsonb | required | [{n, say, check}] |
| step_count | smallint | required |  |
| est_minutes | smallint | required |  |
| reversible | boolean | required; default true |  |
| needs_tools | boolean | required; default false |  |
| opens_panel | boolean | required; default false |  |
| manual_doc_id | uuid | → kb_document |  |
| manual_page | smallint |  |  |
| worst_case | text | required | stated worst outcome of doing the fix |
| reviewer_name | text |  |  |
| reviewer_role | text |  |  |
| reviewed_on | date |  |  |
| review_due | date |  |  |
| status | text | required; values: draft / active / review_due / retired; default 'draft' |  |
| created_at | timestamptz | required |  |

Table rules:
- `CHECK (jsonb_array_length(steps) = step_count)`
- `CHECK (status <> 'active' OR (reversible AND NOT needs_tools AND reviewer_name IS NOT NULL AND reviewed_on IS NOT NULL AND manual_doc_id IS NOT NULL))`
- `CHECK (NOT opens_panel OR manual_doc_id IS NOT NULL)`

### urgency_rule

Rules the agent applies to set an urgency class. Starting values only.

| Column | Type | Constraints and values | Note |
|---|---|---|---|
| id | uuid | PK |  |
| code | text | required; unique |  |
| class | text | required; values: safety / urgent / standard / planned |  |
| category_code | text | → appliance_category | null = any category |
| description | text | required |  |
| condition | jsonb | required; default '{}' | facts that must be true |
| protective_message | text |  | sent at once when the rule fires |
| source | text | required; values: keepwell_hypothesis / oem / centre / regulation; default 'keepwell_hypothesis' |  |
| active | boolean | required; default true |  |
| created_at | timestamptz | required |  |

## 2. Parties: centres, brands' retailers, parts network

### service_centre

| Column | Type | Constraints and values | Note |
|---|---|---|---|
| id | uuid | PK |  |
| name | text | required |  |
| address_line | text | required |  |
| pincode | text | required |  |
| location | geography(Point,4326) |  |  |
| service_pincodes | text[] | required; default '{}' |  |
| categories | text[] | required; default '{}' |  |
| hours | jsonb | required; default '{}' |  |
| default_language | text | required; default 'en' |  |
| onboarding_status | text | required; values: invited / documents_pending / verified / active / suspended; default 'invited' |  |
| created_at | timestamptz | required |  |
| updated_at | timestamptz | required |  |

### centre_commercial  (centre-owned)

Private to the centre: commercial terms with Keepwell.

| Column | Type | Constraints and values | Note |
|---|---|---|---|
| centre_id | uuid | PK; → service_centre |  |
| commission_terms | jsonb | required; default '{}' |  |
| payout_ref | text |  |  |

### centre_channel

The numbers and lines Keepwell answers on for a centre (one WhatsApp number per centre).

| Column | Type | Constraints and values | Note |
|---|---|---|---|
| id | uuid | PK |  |
| centre_id | uuid | required; → service_centre |  |
| channel | text | required; values: voice / whatsapp / sms |  |
| number_ref | text | required | number as dialled by households |
| provider_ref | text |  |  |
| status | text | required; values: pending / active / paused; default 'active' |  |

Table rules:
- `UNIQUE (channel, number_ref)`

### centre_brand_authorisation

Which brands a centre may service and at what level. The agent checks this before it accepts a job; it never recommends a centre.

| Column | Type | Constraints and values | Note |
|---|---|---|---|
| id | uuid | PK |  |
| centre_id | uuid | required; → service_centre |  |
| brand_id | uuid | required; → brand |  |
| level | text | required; values: authorised_service / installation_only / independent |  |
| valid_from | date | required |  |
| valid_to | date |  |  |
| evidence_ref | text |  |  |

Table rules:
- `CHECK (valid_to IS NULL OR valid_to > valid_from)`
- `UNIQUE (centre_id, brand_id, level, valid_from)`

### centre_capacity

| Column | Type | Constraints and values | Note |
|---|---|---|---|
| id | uuid | PK |  |
| centre_id | uuid | required; → service_centre |  |
| category_code | text | required; → appliance_category |  |
| job_type | text | required |  |
| daily_slots | smallint | required |  |
| urgent_holdback | smallint | required; default 0 |  |

Table rules:
- `UNIQUE (centre_id, category_code, job_type)`

### centre_price  (centre-owned)

Private to the centre: its own visit fee and labour.

| Column | Type | Constraints and values | Note |
|---|---|---|---|
| id | uuid | PK |  |
| centre_id | uuid | required; → service_centre; set from session centre |  |
| category_code | text | required; → appliance_category |  |
| job_type | text | required |  |
| complexity_band | text | required; values: basic / standard / complex |  |
| visit_fee_paise | bigint | required |  |
| labour_paise | bigint | required |  |
| valid_from | date | required |  |
| valid_to | date |  |  |

Table rules:
- `CHECK (valid_to IS NULL OR valid_to > valid_from)`
- `UNIQUE (centre_id, category_code, job_type, complexity_band, valid_from)`

### retailer

| Column | Type | Constraints and values | Note |
|---|---|---|---|
| id | uuid | PK |  |
| name | text | required |  |
| city | text |  |  |
| created_at | timestamptz | required |  |

### technician  (centre-owned)

| Column | Type | Constraints and values | Note |
|---|---|---|---|
| id | uuid | PK |  |
| centre_id | uuid | required; → service_centre; set from session centre |  |
| name | text | required |  |
| phone_enc | bytea | required |  |
| phone_hash | bytea | required; unique |  |
| languages | text[] | required; default '{}' |  |
| shift_start | time | required; default '09:00' |  |
| shift_end | time | required; default '18:00' |  |
| route_anchor_type | text | required; values: centre / home / custom; default 'centre' |  |
| route_anchor | geography(Point,4326) |  |  |
| vehicle_type | text |  |  |
| tool_kit | text[] | required; default '{}' |  |
| identity_verified | boolean | required; default false |  |
| safety_certs | text[] | required; default '{}' |  |
| active | boolean | required; default true |  |
| created_at | timestamptz | required |  |
| updated_at | timestamptz | required |  |

### technician_skill  (centre-owned)

| Column | Type | Constraints and values | Note |
|---|---|---|---|
| id | uuid | PK |  |
| technician_id | uuid | required; → technician |  |
| centre_id | uuid | required; → service_centre; set from session centre |  |
| brand_id | uuid | → brand |  |
| category_code | text | required; → appliance_category |  |
| fault_class | text | required |  |
| level | smallint | required |  |
| certified_on | date |  |  |
| certificate_ref | text |  |  |

### technician_availability  (centre-owned)

| Column | Type | Constraints and values | Note |
|---|---|---|---|
| id | uuid | PK |  |
| technician_id | uuid | required; → technician |  |
| centre_id | uuid | required; → service_centre; set from session centre |  |
| slot_start | timestamptz | required |  |
| slot_end | timestamptz | required |  |
| status | text | required; values: open / held / booked / blocked; default 'open' |  |
| held_until | timestamptz |  |  |
| visit_id | uuid |  |  |

Table rules:
- `CHECK (slot_end > slot_start)`
- `EXCLUDE USING gist (technician_id WITH =, tstzrange(slot_start, slot_end) WITH &&)`

### technician_metrics  (centre-owned)

| Column | Type | Constraints and values | Note |
|---|---|---|---|
| technician_id | uuid | required; → technician |  |
| centre_id | uuid | required; → service_centre; set from session centre |  |
| category_code | text | required |  |
| period_end | date | required |  |
| jobs | integer | required |  |
| first_time_fix_rate | numeric(5,4) |  |  |
| on_time_rate | numeric(5,4) |  |  |
| repeat_visit_rate_30d | numeric(5,4) |  |  |
| acceptance_rate | numeric(5,4) |  |  |
| avg_quote_variance_pct | numeric(7,2) |  |  |
| computed_at | timestamptz | required |  |

### parts_centre

| Column | Type | Constraints and values | Note |
|---|---|---|---|
| id | uuid | PK |  |
| name | text | required |  |
| address_line | text | required |  |
| pincode | text | required |  |
| location | geography(Point,4326) |  |  |
| hours | jsonb | required; default '{}' |  |
| pickup_supported | boolean | required; default true |  |
| delivery_supported | boolean | required; default false |  |
| fill_rate | numeric(5,4) |  |  |
| stock_accuracy | numeric(5,4) |  |  |
| active | boolean | required; default true |  |
| created_at | timestamptz | required |  |
| updated_at | timestamptz | required |  |

### parts_centre_brand

| Column | Type | Constraints and values | Note |
|---|---|---|---|
| parts_centre_id | uuid | required; → parts_centre |  |
| brand_id | uuid | required; → brand |  |
| is_authorised | boolean | required; default false |  |

### part_catalogue

| Column | Type | Constraints and values | Note |
|---|---|---|---|
| id | uuid | PK |  |
| brand_id | uuid | required; → brand |  |
| part_no | text | required |  |
| name | text | required |  |
| kind | text | required; values: genuine / aftermarket |  |
| substitution_group | text |  |  |
| mrp_paise | bigint | required |  |
| warranty_months | smallint | required; default 0 |  |

Table rules:
- `UNIQUE (brand_id, part_no)`

### part_compatibility

| Column | Type | Constraints and values | Note |
|---|---|---|---|
| part_id | uuid | required; → part_catalogue |  |
| model_id | uuid | required; → appliance_model |  |
| revision | text | required; default '' |  |

### stock

centre_id is the owning centre for van and centre stock; null for the shared parts network, whose stock every centre may read.

| Column | Type | Constraints and values | Note |
|---|---|---|---|
| id | uuid | PK |  |
| holder_type | text | required; values: van / centre / parts_centre |  |
| holder_id | uuid | required |  |
| centre_id | uuid | → service_centre |  |
| part_id | uuid | required; → part_catalogue |  |
| quantity | integer | required |  |
| as_of | timestamptz | required |  |
| source | text | required; values: scan / call / feed / manual |  |
| confidence | numeric(3,2) | required; default 0.50 |  |

Table rules:
- `UNIQUE (holder_type, holder_id, part_id)`
- `CHECK ((holder_type = 'parts_centre') = (centre_id IS NULL))`

## 3. Identity and memory: global households and appliances

### community

| Column | Type | Constraints and values | Note |
|---|---|---|---|
| id | uuid | PK |  |
| name | text | required |  |
| pincode | text | required |  |
| location | geography(Point,4326) |  |  |
| contact_ref | text |  |  |
| created_at | timestamptz | required |  |

### household

One row per household across all centres. The key is the verified phone.

| Column | Type | Constraints and values | Note |
|---|---|---|---|
| id | uuid | PK |  |
| phone_enc | bytea | required |  |
| phone_hash | bytea | required; unique |  |
| phone_verified_at | timestamptz |  | null = provisional record |
| verified_via | text | values: call_line / otp / brand_record / retailer_record |  |
| language | text | required; default 'en' |  |
| address_line | text |  |  |
| pincode | text |  |  |
| location | geography(Point,4326) |  |  |
| location_verified | boolean | required; default false |  |
| community_id | uuid | → community |  |
| access_notes | jsonb | required; default '{}' |  |
| preferred_slots | jsonb | required; default '{}' |  |
| status | text | required; values: active / paused / closed / merged; default 'active' |  |
| merged_into_id | uuid | → household |  |
| created_at | timestamptz | required |  |
| updated_at | timestamptz | required |  |

### household_member

| Column | Type | Constraints and values | Note |
|---|---|---|---|
| id | uuid | PK |  |
| household_id | uuid | required; → household |  |
| name | text |  |  |
| phone_enc | bytea | required |  |
| phone_hash | bytea | required; unique |  |
| role | text | required; values: owner / family / tenant; default 'family' |  |
| may_raise_ticket | boolean | required; default true |  |
| created_at | timestamptz | required |  |

### household_centre_link

Which centres have served or been contacted by a household. This link is what lets a centre see the household record, and it records the centre that last served the household: only that centre sends reminders.

| Column | Type | Constraints and values | Note |
|---|---|---|---|
| household_id | uuid | required; → household |  |
| centre_id | uuid | required; → service_centre |  |
| first_contact_at | timestamptz | required |  |
| last_served_at | timestamptz |  |  |
| contact_count | integer | required; default 1 |  |

### appliance

One row per physical appliance. Verified rows are keyed by brand + serial. A provisional row (no serial yet) is merged later through identity_merge.

| Column | Type | Constraints and values | Note |
|---|---|---|---|
| id | uuid | PK |  |
| household_id | uuid | required; → household |  |
| category_code | text | required; → appliance_category |  |
| brand_id | uuid | required; → brand |  |
| model_id | uuid | → appliance_model |  |
| model_text | text |  |  |
| serial_no | text |  |  |
| serial_norm | text |  | upper-case, no spaces or dashes |
| identity_status | text | required; values: provisional / verified / merged; default 'provisional' |  |
| merged_into_id | uuid | → appliance |  |
| first_seen_via | text | values: household / brand / retailer / centre |  |
| first_seen_centre_id | uuid | → service_centre |  |
| purchase_date | date |  |  |
| purchase_source | text |  |  |
| invoice_file_ref | text |  |  |
| install_date | date |  |  |
| installed_by | uuid | → technician |  |
| warranty_start | date |  |  |
| warranty_end | date |  |  |
| coverage_plan_id | uuid | → coverage_plan |  |
| usage_profile | jsonb | required; default '{}' |  |
| room | text |  |  |
| care_index | smallint |  |  |
| care_index_reasons | jsonb | required; default '[]' |  |
| care_index_updated_at | timestamptz |  |  |
| last_service_at | date |  |  |
| last_served_centre_id | uuid | → service_centre |  |
| next_due_at | date |  |  |
| status | text | required; values: active / retired / sold; default 'active' |  |
| created_at | timestamptz | required |  |
| updated_at | timestamptz | required |  |

Table rules:
- `CHECK (warranty_end IS NULL OR warranty_start IS NULL OR warranty_end >= warranty_start)`
- `CHECK (identity_status <> 'verified' OR serial_norm IS NOT NULL)`
- `CHECK ((identity_status = 'merged') = (merged_into_id IS NOT NULL))`

### external_ref

Numbers and ids that belong to someone else's system: a centre's own customer number, a brand's case id, a retailer's order id, a phone seen before it was verified. Lookup goes through here so one entity can be found from any party's reference without changing its Keepwell id.

| Column | Type | Constraints and values | Note |
|---|---|---|---|
| id | uuid | PK |  |
| entity_type | text | required; values: household / appliance / ticket / centre / technician |  |
| entity_id | uuid | required |  |
| ref_type | text | required; values: phone / serial / order_id / invoice_no / brand_case_id / centre_customer_no / whatsapp_number / email |  |
| ref_norm | text | required | normalised value; phones are stored as keyed hash (hex) |
| owner_type | text | required; values: keepwell / centre / brand / retailer |  |
| owner_id | uuid |  |  |
| verified | boolean | required; default false |  |
| first_seen_at | timestamptz | required |  |

Table rules:
- `UNIQUE (ref_type, ref_norm, owner_type, owner_id)`

### identity_merge  (app output)

Audit trail for merges. A merge can be reversed; the old row is kept.

| Column | Type | Constraints and values | Note |
|---|---|---|---|
| id | uuid | PK |  |
| entity_type | text | required; values: household / appliance |  |
| from_id | uuid | required |  |
| into_id | uuid | required |  |
| reason | text | required |  |
| evidence | jsonb | required; default '{}' |  |
| merged_by | text | required |  |
| merged_at | timestamptz | required |  |
| reversed_at | timestamptz |  |  |

Table rules:
- `CHECK (from_id <> into_id)`

## 4. Configuration

### scoring_config

| Column | Type | Constraints and values | Note |
|---|---|---|---|
| id | uuid | PK |  |
| kind | text | required; values: assignment / parts_ranking / care_index / batching / urgency |  |
| name | text | required |  |
| weights | jsonb | required; default '{}' |  |
| params | jsonb | required; default '{}' |  |
| valid_from | timestamptz | required |  |
| valid_to | timestamptz |  |  |
| created_by | text |  |  |

Table rules:
- `CHECK (valid_to IS NULL OR valid_to > valid_from)`

## 5. Work: a case from trigger to closure. Every row carries centre_id.

### brand_referral  (centre-owned)

A brand-forwarded request as received.

| Column | Type | Constraints and values | Note |
|---|---|---|---|
| id | uuid | PK |  |
| centre_id | uuid | required; → service_centre; set from session centre |  |
| brand_id | uuid | required; → brand |  |
| brand_request_ref | text | required |  |
| received_at | timestamptz | required |  |
| payload | jsonb | required; default '{}' |  |
| claimed_entitlement | text | values: brand_warranty / extended_warranty / amc / none |  |
| authority_checked | text | values: authorised_service / installation_only / independent / none |  |
| household_contacted_at | timestamptz |  |  |
| status | text | required; values: received / household_contacted / case_opened / declined / duplicate; default 'received' |  |

Table rules:
- `UNIQUE (brand_id, brand_request_ref)`

### retailer_handover  (centre-owned)

A retailer handover (sale with installation or demo).

| Column | Type | Constraints and values | Note |
|---|---|---|---|
| id | uuid | PK |  |
| centre_id | uuid | required; → service_centre; set from session centre |  |
| retailer_id | uuid | required; → retailer |  |
| order_ref | text | required |  |
| invoice_no | text |  |  |
| purchase_date | date |  |  |
| requested_job | text | required; values: installation / demo / uninstall_reinstall |  |
| payload | jsonb | required; default '{}' |  |
| received_at | timestamptz | required |  |
| status | text | required; values: received / household_contacted / case_opened / declined; default 'received' |  |

Table rules:
- `UNIQUE (retailer_id, order_ref)`

### ticket  (centre-owned)

| Column | Type | Constraints and values | Note |
|---|---|---|---|
| id | uuid | PK |  |
| centre_id | uuid | required; → service_centre; set from session centre |  |
| household_id | uuid | required; → household |  |
| appliance_id | uuid | → appliance |  |
| trigger | text | required; values: household_call / household_message / brand_forward / retailer_handover |  |
| channel | text | required; values: voice / whatsapp / sms / app / brand_api / retailer_api / centre_console |  |
| job_type | text | required; values: installation / preventive_service / repair / coverage_claim / uninstall_reinstall / inspection_advice |  |
| brand_referral_id | uuid | → brand_referral |  |
| retailer_handover_id | uuid | → retailer_handover |  |
| origin_reminder_id | uuid |  | set when the household replied to a reminder |
| raw_inputs | jsonb | required; default '[]' |  |
| case_card | jsonb | required; default '{}' |  |
| urgency_class | text | required; values: safety / urgent / standard / planned; default 'standard' |  |
| needed_by | timestamptz |  | stated by the household; separate from urgency |
| safety_flag | boolean | required; default false |  |
| safety_reason | text |  |  |
| entitlement | text | values: brand_warranty / extended_warranty / amc / paid |  |
| coverage_plan_id | uuid | → coverage_plan |  |
| visit_address | text |  |  |
| visit_location | geography(Point,4326) |  |  |
| status | text | required; values: new / triage / clarifying / self_fix / diagnosed / awaiting_slot / booked / scheduled / in_progress / needs_part / completed / closed / cancelled / escalated; default 'new' |  |
| resolution | text | values: self_fix / visit / advice_only / cancelled / duplicate |  |
| first_visit_by | timestamptz |  |  |
| closure_otp_ref | text |  | provider reference; the code itself is never stored |
| closure_confirmed_at | timestamptz |  |  |
| created_at | timestamptz | required |  |
| updated_at | timestamptz | required |  |
| closed_at | timestamptz |  |  |

Table rules:
- `CHECK (appliance_id IS NOT NULL OR job_type = 'installation')`
- `CHECK (NOT safety_flag OR urgency_class = 'safety')`
- `CHECK (status <> 'closed' OR closure_confirmed_at IS NOT NULL)`
- `CHECK (closure_confirmed_at IS NULL OR closure_otp_ref IS NOT NULL)`
- `CHECK ((trigger = 'brand_forward') = (brand_referral_id IS NOT NULL))`
- `CHECK ((trigger = 'retailer_handover') = (retailer_handover_id IS NOT NULL))`

### conversation  (centre-owned)

One row per conversation. A case can have several: a call, then a video session started from it, then a later message.

| Column | Type | Constraints and values | Note |
|---|---|---|---|
| id | uuid | PK |  |
| centre_id | uuid | required; → service_centre; set from session centre |  |
| ticket_id | uuid | → ticket |  |
| household_id | uuid | → household |  |
| channel | text | required; values: voice / whatsapp / sms / app / video |  |
| modality | text | required; values: voice / text / video |  |
| parent_conversation_id | uuid | → conversation |  |
| language | text |  |  |
| started_at | timestamptz | required |  |
| ended_at | timestamptz |  |  |
| end_reason | text | values: completed / household_left / switched_to_video / link_not_opened / timeout / connection_lost / safety_stop |  |
| recording_consent | boolean | required; default false |  |
| transcript_uri | text |  |  |
| summary | text |  |  |

### urgency_assessment  (centre-owned)

| Column | Type | Constraints and values | Note |
|---|---|---|---|
| id | uuid | PK |  |
| centre_id | uuid | required; → service_centre; set from session centre |  |
| ticket_id | uuid | required; → ticket |  |
| class | text | required; values: safety / urgent / standard / planned |  |
| rule_codes | text[] | required; default '{}' |  |
| facts | jsonb | required; default '{}' | answers to the three fact questions |
| assessed_by | text | required; values: agent / centre_console |  |
| reason | text | required |  |
| protective_steps_sent | boolean | required; default false |  |
| created_at | timestamptz | required |  |

### consent_gate  (centre-owned)

Consent gates asked before any self-fix. Gate 1: okay to try a safe fix. Gate 2: only after a yes, switch to video or carry on here. Silence is no.

| Column | Type | Constraints and values | Note |
|---|---|---|---|
| id | uuid | PK |  |
| centre_id | uuid | required; → service_centre; set from session centre |  |
| ticket_id | uuid | required; → ticket |  |
| conversation_id | uuid | → conversation |  |
| gate | smallint | required; values: 1 / 2 |  |
| asked_at | timestamptz | required |  |
| answer | text | required; values: yes / no / silence / not_asked |  |
| answered_at | timestamptz |  |  |
| choice | text | values: continue_here / switch_to_video |  |
| not_asked_reason | text | values: safety_flag / job_type / gate1_not_yes / household_unreachable |  |

Table rules:
- `UNIQUE (ticket_id, gate)`
- `CHECK ((answer = 'not_asked') = (not_asked_reason IS NOT NULL))`
- `CHECK (gate = 2 OR choice IS NULL)`
- `CHECK (choice IS NULL OR answer = 'yes')`

### clarifying_qa  (centre-owned)

| Column | Type | Constraints and values | Note |
|---|---|---|---|
| id | uuid | PK |  |
| centre_id | uuid | required; → service_centre; set from session centre |  |
| ticket_id | uuid | required; → ticket |  |
| conversation_id | uuid | → conversation |  |
| seq | smallint | required |  |
| question | text | required |  |
| answer | text |  |  |
| answer_source | text | values: voice / text / photo / video_observation / brand_payload / retailer_payload / history |  |
| asked_at | timestamptz | required |  |

Table rules:
- `UNIQUE (ticket_id, seq)`

### diagnosis_session  (centre-owned)

A Gemini Live session used for video diagnosis. The 2-minute audio+video cap without compression is why compression and resumption are recorded.

| Column | Type | Constraints and values | Note |
|---|---|---|---|
| id | uuid | PK |  |
| centre_id | uuid | required; → service_centre; set from session centre |  |
| ticket_id | uuid | required; → ticket |  |
| conversation_id | uuid | → conversation |  |
| provider | text | required; default 'gemini_live' |  |
| model | text |  |  |
| link_route | text | required; values: in_app / whatsapp_link / sms_link / same_session |  |
| started_at | timestamptz | required |  |
| ended_at | timestamptz |  |  |
| duration_s | integer |  |  |
| video_on | boolean | required; default true |  |
| compression_on | boolean | required; default true |  |
| resumptions | smallint | required; default 0 |  |
| frames_consent | boolean | required; default false |  |
| end_reason | text | values: completed / household_stopped / safety_stop / timeout / connection_lost |  |
| observations | jsonb | required; default '[]' | what the agent saw: [{t_s, note}] |

### diagnosis_media  (centre-owned)

| Column | Type | Constraints and values | Note |
|---|---|---|---|
| id | uuid | PK |  |
| centre_id | uuid | required; → service_centre; set from session centre |  |
| session_id | uuid | required; → diagnosis_session |  |
| kind | text | required; values: frame / clip / audio |  |
| storage_uri | text | required |  |
| retain_until | date | required |  |
| created_at | timestamptz | required |  |

### fix_attempt  (centre-owned)

What was tried. One row per safe fix offered after gate 1 was a yes.

| Column | Type | Constraints and values | Note |
|---|---|---|---|
| id | uuid | PK |  |
| centre_id | uuid | required; → service_centre; set from session centre |  |
| ticket_id | uuid | required; → ticket |  |
| catalogue_id | uuid | required; → safe_fix_catalogue |  |
| conversation_id | uuid | → conversation |  |
| session_id | uuid | → diagnosis_session |  |
| offered_at | timestamptz | required |  |
| started_at | timestamptz |  |  |
| ended_at | timestamptz |  |  |
| steps_done | smallint | required; default 0 |  |
| outcome | text | required; values: worked / not_worked / abandoned / safety_stop |  |
| household_report | text |  |  |
| observed_on_video | boolean | required; default false |  |

### appliance_event

| Column | Type | Constraints and values | Note |
|---|---|---|---|
| id | uuid | PK |  |
| appliance_id | uuid | required; → appliance |  |
| centre_id | uuid | → service_centre | centre that recorded it; null for platform events |
| event_type | text | required; values: purchase / install / service / repair / part_replaced / self_fix / advice_given / reminder_sent / index_change / warranty_change / merge / note |  |
| visibility | text | required; values: technical / private; default 'technical' |  |
| occurred_at | timestamptz | required |  |
| ticket_id | uuid | → ticket |  |
| details | jsonb | required; default '{}' | technical details only; no prices or notes on the centre |

### visit_plan  (centre-owned, app output)

| Column | Type | Constraints and values | Note |
|---|---|---|---|
| id | uuid | PK |  |
| centre_id | uuid | required; → service_centre; set from session centre |  |
| ticket_id | uuid | required; → ticket |  |
| version | integer | required; default 1 |  |
| trigger_reason | text | required; values: initial / self_fix_failed / new_info / reclassified / brand_info; default 'initial' |  |
| already_tried | jsonb | required; default '[]' | fix attempts and checks done before this plan |
| required_skills | jsonb | required; default '[]' |  |
| est_duration_p50_min | integer |  |  |
| est_duration_p80_min | integer |  |  |
| tools_needed | text[] | required; default '{}' |  |
| requires_safety_cert | text[] | required; default '{}' |  |
| access_notes | text |  |  |
| confidence | numeric(3,2) |  |  |
| model_version | text |  |  |
| created_at | timestamptz | required |  |

Table rules:
- `UNIQUE (ticket_id, version)`
- `CHECK (est_duration_p80_min IS NULL OR est_duration_p50_min IS NULL OR est_duration_p80_min >= est_duration_p50_min)`

### plan_hypothesis  (centre-owned, app output)

| Column | Type | Constraints and values | Note |
|---|---|---|---|
| id | uuid | PK |  |
| centre_id | uuid | required; → service_centre; set from session centre |  |
| visit_plan_id | uuid | required; → visit_plan |  |
| rank | smallint | required |  |
| cause | text | required |  |
| probability | numeric(4,3) | required |  |
| evidence | jsonb | required; default '[]' |  |

Table rules:
- `UNIQUE (visit_plan_id, rank)`

### plan_part  (centre-owned, app output)

| Column | Type | Constraints and values | Note |
|---|---|---|---|
| id | uuid | PK |  |
| centre_id | uuid | required; → service_centre; set from session centre |  |
| visit_plan_id | uuid | required; → visit_plan |  |
| part_id | uuid | required; → part_catalogue |  |
| probability | numeric(4,3) | required |  |
| quantity | smallint | required; default 1 |  |

Table rules:
- `UNIQUE (visit_plan_id, part_id)`

### assignment_candidate  (centre-owned, app output)

The agent's ranked technician candidates inside the centre. The centre can reassign from its console; the override and its reason are logged and used as a training signal.

| Column | Type | Constraints and values | Note |
|---|---|---|---|
| id | uuid | PK |  |
| centre_id | uuid | required; → service_centre; set from session centre |  |
| ticket_id | uuid | required; → ticket |  |
| visit_plan_id | uuid | required; → visit_plan |  |
| technician_id | uuid | required; → technician |  |
| slot_start | timestamptz | required |  |
| slot_end | timestamptz | required |  |
| rank | smallint | required |  |
| score | numeric(6,3) |  |  |
| score_breakdown | jsonb | required; default '{}' |  |
| config_id | uuid | → scoring_config |  |
| outcome | text | required; values: proposed / chosen / not_chosen; default 'proposed' |  |
| chosen_by | text | values: agent / centre_console |  |
| override_reason | text |  |  |
| created_at | timestamptz | required |  |

Table rules:
- `CHECK (slot_end > slot_start)`
- `CHECK (chosen_by <> 'centre_console' OR override_reason IS NOT NULL OR outcome <> 'chosen')`

### slot_proposal  (centre-owned, app output)

The slots put to the household for one technician and window.

| Column | Type | Constraints and values | Note |
|---|---|---|---|
| id | uuid | PK |  |
| centre_id | uuid | required; → service_centre; set from session centre |  |
| ticket_id | uuid | required; → ticket |  |
| candidate_id | uuid | → assignment_candidate |  |
| slot_start | timestamptz | required |  |
| slot_end | timestamptz | required |  |
| price_low_paise | bigint |  |  |
| price_high_paise | bigint |  |  |
| shown_at | timestamptz |  |  |
| accepted | boolean |  |  |
| accepted_at | timestamptz |  |  |
| expires_at | timestamptz |  |  |

Table rules:
- `CHECK (slot_end > slot_start)`

### quote  (centre-owned)

| Column | Type | Constraints and values | Note |
|---|---|---|---|
| id | uuid | PK |  |
| centre_id | uuid | required; → service_centre; set from session centre |  |
| ticket_id | uuid | required; → ticket |  |
| version | integer | required; default 1 |  |
| quote_type | text | required; values: estimate / firm |  |
| valid_until | timestamptz |  |  |
| approved_at | timestamptz |  |  |
| approval_channel | text | values: whatsapp / app / in_person / voice |  |
| approval_ref | text |  |  |
| created_at | timestamptz | required |  |

Table rules:
- `UNIQUE (ticket_id, version)`

### quote_line  (centre-owned)

| Column | Type | Constraints and values | Note |
|---|---|---|---|
| id | uuid | PK |  |
| centre_id | uuid | required; → service_centre; set from session centre |  |
| quote_id | uuid | required; → quote |  |
| line_type | text | required; values: visit_fee / labour / part / travel / discount / tax |  |
| description | text | required |  |
| part_id | uuid | → part_catalogue |  |
| quantity | numeric(8,2) | required; default 1 |  |
| amount_paise | bigint | required |  |
| payer | text | required; values: brand_warranty / extended_warranty / amc / household / keepwell |  |
| plan_id | uuid | → coverage_plan |  |

Table rules:
- `CHECK (line_type <> 'part' OR part_id IS NOT NULL)`

### visit  (centre-owned)

| Column | Type | Constraints and values | Note |
|---|---|---|---|
| id | uuid | PK |  |
| centre_id | uuid | required; → service_centre; set from session centre |  |
| ticket_id | uuid | required; → ticket |  |
| technician_id | uuid | required; → technician |  |
| planned_start | timestamptz | required |  |
| planned_end | timestamptz | required |  |
| is_return_visit | boolean | required; default false |  |
| parent_visit_id | uuid | → visit |  |
| check_in_at | timestamptz |  |  |
| check_in_location | geography(Point,4326) |  |  |
| check_out_at | timestamptz |  |  |
| checklist | jsonb | required; default '[]' |  |
| outcome | text | values: fixed / partial / needs_part / not_repairable / no_access |  |
| outcome_notes | text |  |  |
| root_cause_confirmed | text |  |  |
| closure_otp_ref | text |  |  |
| closure_confirmed_at | timestamptz |  |  |
| rating | smallint |  |  |
| created_at | timestamptz | required |  |
| updated_at | timestamptz | required |  |

Table rules:
- `CHECK (planned_end > planned_start)`
- `CHECK (closure_confirmed_at IS NULL OR closure_otp_ref IS NOT NULL)`

### visit_media  (centre-owned, app output)

| Column | Type | Constraints and values | Note |
|---|---|---|---|
| id | uuid | PK |  |
| centre_id | uuid | required; → service_centre; set from session centre |  |
| visit_id | uuid | required; → visit |  |
| kind | text | required; values: before / after / part / voice_note / invoice |  |
| storage_uri | text | required |  |
| created_at | timestamptz | required |  |

### visit_part_used  (centre-owned)

| Column | Type | Constraints and values | Note |
|---|---|---|---|
| id | uuid | PK |  |
| centre_id | uuid | required; → service_centre; set from session centre |  |
| visit_id | uuid | required; → visit |  |
| part_id | uuid | required; → part_catalogue |  |
| serial_no | text |  |  |
| quantity | smallint | required; default 1 |  |
| source_type | text | values: van / centre / parts_centre / courier / household |  |

### reservation  (centre-owned)

| Column | Type | Constraints and values | Note |
|---|---|---|---|
| id | uuid | PK |  |
| centre_id | uuid | required; → service_centre; set from session centre |  |
| part_id | uuid | required; → part_catalogue |  |
| quantity | smallint | required; default 1 |  |
| holder_type | text | required; values: van / centre / parts_centre |  |
| holder_id | uuid | required |  |
| visit_id | uuid | required; → visit |  |
| ready_by | timestamptz | required |  |
| status | text | required; values: requested / confirmed / collected / released / expired; default 'requested' |  |
| created_at | timestamptz | required |  |

### route  (centre-owned)

| Column | Type | Constraints and values | Note |
|---|---|---|---|
| id | uuid | PK |  |
| centre_id | uuid | required; → service_centre; set from session centre |  |
| technician_id | uuid | required; → technician |  |
| route_date | date | required |  |
| batched | boolean | required; default false |  |
| optimiser | text | required; values: manual / or_tools / route_optimization_api; default 'manual' |  |
| planned_travel_min | integer |  |  |
| actual_travel_min | integer |  |  |
| created_at | timestamptz | required |  |

Table rules:
- `UNIQUE (technician_id, route_date)`

### route_stop  (centre-owned)

| Column | Type | Constraints and values | Note |
|---|---|---|---|
| route_id | uuid | required; → route |  |
| centre_id | uuid | required; → service_centre; set from session centre |  |
| seq | smallint | required |  |
| visit_id | uuid | required; unique; → visit |  |
| planned_arrival | timestamptz |  |  |
| actual_arrival | timestamptz |  |  |

### settlement_line  (centre-owned)

| Column | Type | Constraints and values | Note |
|---|---|---|---|
| id | uuid | PK |  |
| centre_id | uuid | required; → service_centre; set from session centre |  |
| ticket_id | uuid | required; → ticket |  |
| party_type | text | required; values: household / brand / plan_provider / centre / parts_centre / keepwell |  |
| party_id | uuid |  |  |
| direction | text | required; values: receivable / payable |  |
| amount_paise | bigint | required |  |
| status | text | required; values: pending / paid / failed / waived; default 'pending' |  |
| payment_ref | text |  |  |
| due_at | timestamptz |  |  |
| settled_at | timestamptz |  |  |

### feedback  (centre-owned)

| Column | Type | Constraints and values | Note |
|---|---|---|---|
| id | uuid | PK |  |
| centre_id | uuid | required; → service_centre; set from session centre |  |
| ticket_id | uuid | required; → ticket |  |
| visit_id | uuid | → visit |  |
| from_type | text | required; values: household / technician / centre |  |
| rating | smallint |  |  |
| reason_codes | text[] | required; default '{}' |  |
| comment | text |  |  |
| is_dispute | boolean | required; default false |  |
| resolution | text |  |  |
| created_at | timestamptz | required |  |

### reminder  (centre-owned)

Reminders are sent only by the centre that last served the appliance, and only with the household's consent for that purpose.

| Column | Type | Constraints and values | Note |
|---|---|---|---|
| id | uuid | PK |  |
| centre_id | uuid | required; → service_centre; set from session centre |  |
| household_id | uuid | required; → household |  |
| appliance_id | uuid | → appliance |  |
| reminder_type | text | required; values: service_due / seasonal / warranty_ending / plan_renewal / consumable / after_repair / rating_request |  |
| due_on | date | required |  |
| template_name | text |  |  |
| whatsapp_category | text | values: utility / marketing / authentication / service |  |
| status | text | required; values: scheduled / sent / delivered / read / acted / snoozed / suppressed / failed; default 'scheduled' |  |
| scheduled_at | timestamptz |  |  |
| sent_at | timestamptz |  |  |
| delivered_at | timestamptz |  |  |
| read_at | timestamptz |  |  |
| action_taken | text |  |  |
| ticket_id | uuid | → ticket |  |
| created_at | timestamptz | required |  |

## 6. Experience layer (L3): anonymised closed jobs with embeddings.

### experience_case

Shared across centres; no household, address or centre link.

| Column | Type | Constraints and values | Note |
|---|---|---|---|
| id | uuid | PK |  |
| source_visit_id | uuid | unique; → visit |  |
| brand_id | uuid | required; → brand |  |
| category_code | text | required; → appliance_category |  |
| model_series | text |  |  |
| pincode | text |  |  |
| symptom_text | text | required |  |
| error_code | text |  |  |
| self_fix_tried | text[] | required; default '{}' | safe_fix_catalogue codes tried before the visit |
| root_cause | text | required |  |
| parts | jsonb | required; default '[]' |  |
| duration_min | integer |  |  |
| cost_paise | bigint |  |  |
| outcome | text | required |  |
| verified_by_technician | boolean | required; default false |  |
| embedding | vector(768) |  |  |
| created_at | timestamptz | required |  |

## 7. Consent and audit

### consent_ledger

| Column | Type | Constraints and values | Note |
|---|---|---|---|
| id | uuid | PK |  |
| subject_type | text | required; values: household / member / technician / centre |  |
| subject_id | uuid | required |  |
| purpose | text | required; values: memory / service_reminders / warranty_alerts / follow_up / share_technical_history / photos_voice / video_diagnosis / frame_retention / analytics |  |
| scope_centre_id | uuid | → service_centre | set for centre-specific purposes such as reminders |
| notice_version | text | required |  |
| granted_at | timestamptz | required |  |
| channel | text | required |  |
| withdrawn_at | timestamptz |  |  |
| evidence | jsonb | required; default '{}' |  |

Table rules:
- `CHECK (withdrawn_at IS NULL OR withdrawn_at >= granted_at)`

### access_log  (app output)

| Column | Type | Constraints and values | Note |
|---|---|---|---|
| id | uuid | PK |  |
| actor_type | text | required; values: technician / centre_user / keepwell_admin / agent / system |  |
| actor_id | text | required |  |
| actor_centre_id | uuid | → service_centre |  |
| record_table | text | required |  |
| record_id | uuid | required |  |
| owner_centre_id | uuid | → service_centre | centre that recorded the data read |
| cross_centre | boolean | required; default false |  |
| ticket_id | uuid | → ticket |  |
| reason | text | required |  |
| occurred_at | timestamptz | required |  |

## Views

- **current_consent**
- **quote_total**
- **quote_variance**
- **first_visit_outcome**: First-time fix: the first visit ended 'fixed' and the ticket had no other visit. Tickets resolved by a self-fix have no visit and do not appear here.
- **appliance_due**: Due within 30 days, with the centre that would send the reminder.
- **tried_summary**: What was tried on a ticket, in order. Feeds the visit plan and the technician brief.
- **safe_fix_effectiveness**: How often each safe fix works. Drives review of the catalogue.

## Functions

- `touch_updated_at() RETURNS trigger LANGUAGE plpgsql AS $$`
- `deny_mutation() RETURNS trigger LANGUAGE plpgsql AS $$`
- `current_centre() RETURNS uuid LANGUAGE plpgsql STABLE AS $$` Session context set by the agent for each call or conversation: SET kw.centre_id = '<uuid>';        the centre whose line this is SET kw.role = 'platform';           Keepwell operations and batch jobs only
- `is_platform() RETURNS boolean LANGUAGE plpgsql STABLE AS $$`
- `centre_authority(p_centre uuid, p_brand uuid, p_on date DEFAULT current_date)` Highest authorisation a centre holds for a brand on a date, or 'none'.
- `identify_household(p_phone_hash bytea, p_phone_enc bytea, p_centre uuid, p_via text DEFAULT 'call_line')` Find or create a household from a phone hash on a centre's line, and link it to that centre. If the household already existed with other centres, the call is logged as a cross-centre lookup. Returns the global id.
- `shared_history_allowed(p_appliance uuid) RETURNS boolean` Does the household that owns this appliance allow technical history to be shared?
- `read_shared_history(p_appliance uuid, p_centre uuid, p_ticket uuid, p_reason text)` Technical history of an appliance for a centre that did not record it. Own rows are always returned. Rows from other centres are returned only when the household has consented; each such read is logged.
- `centre_knows_household(p_household uuid) RETURNS boolean` Households and appliances: visible to a centre only through household_centre_link.
