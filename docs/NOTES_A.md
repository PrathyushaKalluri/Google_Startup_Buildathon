# Part A Reading Notes (`docs/NOTES_A.md`)

Prepared before writing Part A code, following Section 4 & Section 7 of `AGENTS.md`.

---

## 1. `contract/SHARED_CONTRACT.md`
1. Keepwell is deployed by service centres and brands; it is the face of the centre/brand, never a centre matchmaker.
2. Four triggers (`household_call`, `household_message`, `brand_forward`, `retailer_handover`) all open the same ticket flow.
3. Mandatory two consent gates before any self-fix: Gate 1 ("okay to try a safe fix?") and Gate 2 ("switch to video or carry on here?"), with silence = no; safety cases skip both (`safety_flag`); non-repair jobs skip both (`job_type`).
4. Six weighted technician assignment factors: fix confidence (30), parts readiness (25), time to visit (20), route cost (15), reliability (5), household fit (5); price is never scored.
5. Backend stack: Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2 + async `psycopg` 3, Google ADK, `google-genai`, MCP at `/mcp`, PostgreSQL 16 (PostGIS, pgvector, pgcrypto, btree_gist), Firestore projections, Cloud Storage, BigQuery.
6. Strict folder ownership: Part A owns `db/`, `services/`, `kb/`, `analytics/`, `evals/`, `infra/backend/`, `.agents/part-a/`, and `docs/*_A.md`. Zero edits in Part B folders.
7. All REST API v1 endpoints under `/v1`, errors `{ "error": { "code", "message", "field", "request_id" } }`, lists `{ "items": [...], "next_cursor": null }`, idempotency keys on writes.
8. Live call protocol at `WS /v1/live/call` uses PCM16 16kHz in / 24kHz out, JSON control frames (`start`, `video_frame`, `image`, `client_state`, `end`), and server frames (`ready`, `transcript`, `video_link`, `modality`, `ui_hint`, `event`, `go_away`, `ended`, `error`).
9. Parts are never invented (must exist in `part_catalogue` + `part_compatibility`); payment never closes a job (OTP only).
10. Metrics defined canonically: FTF (`first_visit_outcome`), FVR-14 (fixed on 1st visit, OTP closed, no same-appliance same-fault repair within 14 days), self-fix resolution, gate funnel, urgency agreement, override rate, parts ready at visit.

## 2. `input/dataset/README.md`
1. Simulation clock is Saturday 21 Nov 2026, 08:00 IST; pilot history starts 1 Sep 2025; agent live from 1 Mar 2026.
2. Seeded world: 9 service centres (`c_av`, `c_zn`, `c_fw`, `c_cc`, `c_aq`, `c_mh`, `c_ip`, `c_ls`, `c_hw`), 37 technicians, 8 parts centres, 144 parts, 7 brands, 5 retailers, 165 households, 297 members, 341 appliances, 395 historical tickets.
3. 57 households are linked to multiple centres, enabling realistic cross-centre history and consent testing.
4. 14 safe-fix catalogue entries (12 active, 1 `review_due`, 1 `retired`) and 12 urgency rules (4 safety, 5 urgent, 1 standard, 2 planned).
5. 829 stock rows across vans, centres, and parts centres; recorded quantity has realistic accuracy noise (`evaluator_only/true_stock.csv` holds ground truth).
6. 674 experience cases with NULL embeddings ready for `gemini-embedding-2` (768d) ingestion.
7. 20 incoming test cases in `inbox/inbox.json` across all 4 triggers; `evaluator_only/` and `gen/` must NEVER be read by runtime application code.
8. Phone hashing uses HMAC-SHA256 with dev key `keepwell-dev-hash-key` on whitespace-stripped numbers (`phone_hash`), plus Fernet `phone_enc`.
9. App-output tables (`visit_plan`, `plan_hypothesis`, `plan_part`, `assignment_candidate`, `slot_proposal`, `visit_media`, `access_log`, `identity_merge`) start empty by design.
10. Only 5 appliance categories are seeded (`ac`, `refrigerator`, `washing_machine`, `ro_purifier`, `geyser`).

## 3. `input/docs/keepwell_design_doc.md`
1. Keepwell is the centre's agent and brand/retailer link; never ranks or recommends another centre (even when out of service area or unauthorised).
2. Six job types: `installation`, `preventive_service`, `repair`, `coverage_claim`, `uninstall_reinstall`, `inspection_advice`.
3. Every repair follows: identify -> safety & authority -> clarify -> Gate 1 -> Gate 2 -> 1 safe fix -> record `what_was_tried` -> re-run diagnosis on failure -> visit plan -> technician & slot -> estimate/firm quote -> visit -> OTP closure -> memory.
4. Safety cases skip both gates, send stop-use message immediately, skip batching, and book earliest qualified technician.
5. Urgent cases book earliest slot first (never batched) and may still offer safe fix while waiting; if fixed, visit cancels.
6. Urgency is decided from rules + 3 fact questions (food/water/health risk; partial usability; duration); never ask "how urgent is it?"; `needed_by` is stored separately.
7. Video sessions require context-window compression and session resumption due to 2-minute audio+video limit; frames are kept only with consent.
8. Parts sourcing follows a 4-tier ladder anchored to the technician's route: (1) van stock -> (2) centre stock -> (3) partner parts centre -> (4) courier.
9. Care index (0–100) is an explainable estimate based on service recency, age, breakdown history, usage load, environment, and open advice.
10. Knowledge base has 6 layers: L1 Appliance catalogue (Postgres), L2 Documents (Gemini File Search), L3 Experience (pgvector), L4 Policy/Price (Postgres), L5 Safety rules (deterministic code), L6 Safe-fix catalogue (Postgres with strict CHECKs).

## 4. `input/docs/keepwell_schema.sql` & `DATA_DICTIONARY.md`
1. Schema lives in namespace `kw` (`SET search_path = kw, public;`), 63 tables, 7 views, 9 functions, full Row-Level Security (RLS) for role `kw_app`.
2. Session variables `kw.centre_id` and `kw.role = 'platform'` drive all RLS policies (`current_centre()`, `is_platform()`).
3. Money is always `bigint` in paise (INR); timestamps are `timestamptz`; locations are PostGIS `geography(Point, 4326)`.
4. Global identity: `household.phone_hash` (unique) and `appliance (brand_id, serial_norm)` (partial unique index where not merged). Aliases live in `external_ref`.
5. `appliance_event` and `access_log` are append-only enforced by `deny_mutation()` triggers and `REVOKE UPDATE, DELETE`.
6. `safe_fix_catalogue` enforces threshold at DB level: `step_count BETWEEN 1 AND 6`, `est_minutes BETWEEN 1 AND 12`, active requires `reversible AND NOT needs_tools AND reviewer_name IS NOT NULL AND manual_doc_id IS NOT NULL`.
7. `consent_gate` enforces `UNIQUE (ticket_id, gate)`, `gate IN (1, 2)`, `(answer = 'not_asked') = (not_asked_reason IS NOT NULL)`, `gate = 2 OR choice IS NULL`.
8. `ticket` enforces `NOT safety_flag OR urgency_class = 'safety'`, `status <> 'closed' OR closure_confirmed_at IS NOT NULL`, `closure_confirmed_at IS NULL OR closure_otp_ref IS NOT NULL`.
9. Cross-centre access is exclusively via `SECURITY DEFINER` functions: `centre_authority()`, `identify_household()`, `shared_history_allowed()`, `read_shared_history()`.
10. Views provided out of the box: `current_consent`, `quote_total`, `quote_variance`, `first_visit_outcome`, `appliance_due`, `tried_summary`, `safe_fix_effectiveness`.

## 5. `input/docs/keepwell_example_queries.sql`
1. Q1–Q4 handle arrival: household phone-hash lookup via `external_ref`, appliance serial lookup, `centre_authority()` decision matrix, and service pincode/capacity checks.
2. Q5–Q11 handle urgency queue ordering (`safety -> urgent -> standard -> planned`, then `needed_by`), consent gate funnel, active safe-fix lookup, `tried_summary`, catalogue health, resolution mix, and centre overrides.
3. Q12–Q16 handle technician hard filters (active, verified, skill >= required, safety certs `@>`, distance, open availability), 3-tier parts ladder, nearby parts centres, same-day batching, and 90-day FTF rate.
4. Q17–Q21 handle `read_shared_history()`, household cross-centre access audit (`access_log`), pgvector cosine similarity on `experience_case`, consent+cap-checked reminders, and appliance timeline.
5. Q22–Q24 handle technician contact release (logged to `access_log` only once slot confirmed), visit OTP closure, and self-fix OTP closure.

## 6. `input/dataset/evaluator_only/CASE_GUIDE.md` & `kw_safe_fix_catalogue.pdf`
1. C03 (Sunita Sharma, `c_fw`, Hindi call, Wavecrest washer E21, warranty expired 22 days ago) is the flagship P0 stage case: Gate 1 yes -> Gate 2 video -> `SF-WM-DRAINFILTER-WC` -> partial drain, E21 returns (`not_worked`) -> diagnosis re-run -> pump housing -> visit plan with `already_tried` -> assignment -> quote -> OTP close.
2. Safety cases C05 (Heatwell geyser tap shock, Hindi call) and C15 (Wavecrest semi-auto washer burning smell/smoke, Hindi call) MUST skip both gates (`not_asked`, `safety_flag`), send stop-use message, and offer zero self-fixes.
3. Brand authority failure case C18 (Aerovane warranty AC sent to independent `c_cc`) MUST return `declined` with reason and never book a warranty visit.
4. Cross-centre consent cases: C19 (`c_aq` receives Heatwell geyser previously at `c_hw`, consent granted -> `read_shared_history` returns technical rows & logs `access_log`) vs C14 (`c_cc`, consent NOT granted -> must NOT read other centres' history).
5. Out-of-area case C11 (Shamshabad 501218 at `c_cc`) MUST decline politely without recommending another centre.
6. Non-repair cases C07 (retailer AC install, work_at_height + gas cert), C08 (preventive service, 3 ACs batched), C20 (retailer washer install, member phone resolves to existing household) MUST record both gates as `not_asked` (`job_type`).
7. Declined self-fix cases C12 (repeat washer fault 18d -> `URG-REPEAT-30D` urgent, Gate 1 no -> Gate 2 `not_asked` with `gate1_not_yes`) and C16 (Telugu AC call, Gate 1 no -> Gate 2 `not_asked`).
8. Safe-fix catalogue (`KW-SF-01 rev B`) contains 14 entries; `SF-AC-RESET` is `review_due` and `SF-GY-LEGACY` is `retired` — neither may ever be offered.
9. Provisional appliance merge cases C09 (blurry sticker) and C13 (`WC-TL70` blurry sticker) must NOT reserve parts until model/serial is confirmed.
10. Repeat complaint within 30 days (C12) waives visit charge and triggers urgent classification (`URG-REPEAT-30D`).

---

## Open Questions & Decisions Logged
- See `docs/DECISIONS_A.md` for local runtime adapter (SQLite + Python RLS mirror when Postgres/Docker is absent on host machine, while keeping full PostgreSQL 16 + `psycopg` 3 + RLS SQL migrations/tests ready for Cloud SQL / Docker) and Gemini model fallback handling.

## Build Order (P0 First)
1. **A0**: Repo layout, `AGENTS.md`, rules, `NOTES_A.md`, `DECISIONS_A.md`, implementation plan artifact.
2. **A1**: Data platform (`db/schema.sql`, additive migration `001_part_a_additions.sql`, idempotent `db/seed/load_seed.py`), `services/common/` (config, auth, RLS session, phone hash/mask, magic links, Model Armor `untrusted_guard.py`, structured logging).
3. **A2**: All 10 pure-Python deterministic engines in `services/agents/engines/` (`authority`, `urgency`, `safefix`, `gates`, `assignment`, `planner`, `parts`, `payments`, `pricing`, `otp`) + 100% unit tests + parts fuzz test.
4. **A3**: Runtime lexicons (`repair_vocabulary.yaml`, `hazard_lexicon.yaml`), ADK agents (`intake`, `identity`, `diagnostic`, `fix_guide`, `planner`, `quote`, `memory`, `orchestrator`), MCP server (`/mcp`), `kb/` ingestion scripts.
5. **A4**: Live bridge (`WS /v1/live/call`) with Gemini Live API + resumption/compression/GoAway + `services/live/prompts/live_agent.md` + `scripted_client.py` + WhatsApp/Brand/Retailer channel adapters.
6. **A5**: Complete REST API v1 (`services/api/`), `openapi.json`, Firestore projection + outbox worker (`services/worker/`), demo & payment & debrief endpoints.
7. **A6**: BigQuery analytics SQL + Looker guide (`analytics/`), 20-case + 100-case eval runner (`evals/`), GCP infra scripts (`infra/backend/`), Part A skills (`.agents/part-a/`), and `docs/HANDOFF_A.md` + `docs/rubric_A.md`.
