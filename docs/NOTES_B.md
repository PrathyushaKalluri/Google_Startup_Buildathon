# Part B Reading Notes (`docs/NOTES_B.md`)

Prepared per Section 4 & Section 7 of `PROMPT_B_experience_surfaces.md` (saved as `AGENTS.md`) before writing application code.

---

## 1. `SHARED_CONTRACT.md` (Frozen v1)

- Keepwell is deployed for service centres and brands (never a household-facing centre matchmaker); one agent answers four triggers (`household_call`, `household_message`, `brand_forward`, `retailer_handover`).
- Two mandatory consent gates precede any self-fix on repair jobs: Gate 1 ("okay to try a safe fix?") and Gate 2 (only after yes: "switch to video, or carry on here?"); silence counts as no; safety cases skip both; non-repair jobs get neither.
- Technical stack for Part B is frozen: Flutter 3.x (stable), Dart 3.x, Material 3 Expressive, one `melos` monorepo (`apps/{kw_ui,kw_client,console,field,household,brand}`), Firebase Auth/Firestore/FCM/App Check/Hosting.
- Money is always integer `paise` (INR); timestamps are UTC ISO 8601 on the wire and `+05:30` IST for display; IDs are UUID strings; languages are BCP 47 (`en`, `hi`, `te`).
- JSON keys and enums are `snake_case` matching `keepwell_schema.sql`; Dart models use `camelCase` with `json_serializable` snake_case mapping and ignore unknown fields.
- REST API v1 (`/v1`) covers centre console, technician, parts centre, brand/retailer, public household magic-link endpoints (including Google Pay & UPI sandbox payments), channel webhooks/simulators, and admin/demo replay endpoints.
- Live state lives in Firestore (read-only for Part B clients; Part A writes projections): `centres/{cid}/{tickets,conversations,feed,technicians,visits,parts_requests}`, `households/{hid}/whatsapp_thread`, and `meta/demo`.
- Live call protocol (`WS /v1/live/call`) exchanges 16 kHz PCM16 mic audio + ≤1 fps JPEG video frames up, and 24 kHz PCM16 agent audio + `ready`, `transcript`, `video_link`, `modality`, `ui_hint`, `event`, `go_away`, `ended`, `error` frames down.
- Strict invariants (C11): parts are never invented (unmatched parts display as `"needs checking"`), safety cases skip gates and go to top of board, and closure is by household OTP only (payment never closes a job).
- Part B is contract-complete when every screen runs against `mocks/` (REST, WebSocket, Firestore emulator) and switching to Part A requires only changing `API_BASE_URL`, `LIVE_WS_URL`, and Firebase project config.

## 2. `keepwell/docs_v1/README.md` (Simulated Dataset v0.2)

- Simulation clock is Saturday 21 Nov 2026, 08:00 IST; historical data runs from 1 Sep 2025, with live agent features active from 1 Mar 2026.
- World scale: 9 service centres (`c_av`, `c_zn`, `c_fw`, `c_cc`, `c_aq`, `c_mh`, `c_ip`, `c_ls`, `c_hw`), 37 technicians, 8 parts centres, 144 parts, 7 brands, 5 retailers, 165 households, 297 members, 341 appliances across 5 categories.
- 395 historical/in-flight tickets (26 in flight for 22–25 Nov; 14 brand requests declined at authority check), 118 self-fix attempts across 14 catalogue entries (12 active, 1 review_due, 1 retired), 369 urgency assessments (9 centre reclassifications).
- 57 households link to multiple centres, enabling realistic cross-centre history sharing and consent-ledger UI testing.
- 20 incoming test cases (`C01`–`C20`) arrive in `inbox/inbox.json` with synthetic `.ogg` calls/voice notes, `.jpg` photos, brand JSONs, and retailer handovers.
- `C03` (Sunita Sharma, Hindi call to `c_fw` Frost and Wave, Wavecrest washer E21, warranty expired 22 days ago) is the flagship stage case: video switch, drain-filter fix fails, diagnosis re-runs, assignment, reassignment, quote, OTP close.
- `evaluator_only/` (`CASE_GUIDE.md`, `ground_truth.json`, `voice_scripts.json`, `true_stock.csv`, `personas/`) must never be read by production app code; Part B uses `voice_scripts.json` only inside `mocks/ws` to script the mock C03 call.
- Stock quantities in `csv/stock.csv` intentionally carry staleness/confidence differences from `true_stock.csv`, which Part B surfaces as stock confidence cues.
- Five appliance categories only: `ac`, `refrigerator`, `washing_machine`, `ro_purifier`, `geyser`.
- Data is intentionally messy (missing models/purchase dates, withdrawn consents, out-of-area pincodes), so every UI screen must handle nulls, provisional identity, and declined/out-of-area states gracefully.

## 3. `keepwell_design_doc.md` (End-to-End Flow & Data Design)

- 12-step snaking flow with 6 human decisions: Identify → Safety/Entitlement → Clarify → Two Consent Gates → Guided Self-Fix → Re-run Diagnosis on Failure → Visit Plan → Technician & Slot → Quote (Estimate → Firm → Approval) → Visit → OTP Closure → Home Memory.
- Urgency is never asked of the household; the agent derives `safety`, `urgent`, `standard`, or `planned` from rules plus up to 3 consequence/dependency fact questions, while `needed_by` is stored separately.
- Safety cases skip self-fix and batching; urgent cases book the earliest slot first and still offer a safe fix while waiting; protective steps (e.g., move milk/medicine, switch off MCB) are sent regardless of Gate 1.
- Technician assignment uses 2 stages: hard filters (centre authority, skill level, travel ETA, availability, safety certs) followed by a 100-point weighted score (Fix confidence 30, Parts readiness 25, Time to visit 20, Route cost 15, Reliability 5, Household fit 5; price is never scored).
- Slot offers show 1 recommended window + at most 2 alternatives (matching WhatsApp's 3-button limit) with factual trust signals (e.g., technician name, photo, and past fix count).
- Parts readiness follows a 4-tier ladder anchored to the technician's route: van stock → own centre stock → partner parts centre → courier.
- Quotes follow Estimate → Firm Quote (on site) → Written Approval with line-level payer splits (`brand_warranty`, `plan_provider`, `household`) and variance tracking.
- Appliance Care Index (0–100: ≥75 good, 50–74 watch, <50 due) is always displayed as an explainable estimate with reasons (service recency, age, breakdown history, usage, open advice); warranty status is separate.
- Knowledge base has 6 layers (L1 Catalogue, L2 File Search PDFs, L3 Experience pgvector, L4 Policy/Price, L5 Deterministic Safety Rules, L6 Safe-Fix Catalogue); every diagnostic claim must carry a citation.
- Stage demo (C03) showcases 8 beats across the call dialer, video-link switch, Live Stage view on console, technician reassignment with reason, technician brief/quote, and OTP closure updating Home Memory.

## 4. `keepwell/docs_v1/keepwell_schema.sql` & `DATA_DICTIONARY.md` (v0.2, 63 Tables)

- Schema lives in namespace `kw` with row-level security (`kw.centre_id`, `kw.role = 'platform'`); operational tables are centre-owned while `household`, `appliance`, and `external_ref` carry global IDs.
- Exact job types: `installation`, `preventive_service`, `repair`, `coverage_claim`, `uninstall_reinstall`, `inspection_advice`.
- Exact urgency classes: `safety`, `urgent`, `standard`, `planned`; exact authority levels: `authorised_service`, `installation_only`, `independent`.
- `safe_fix_catalogue` enforces the safe-fix threshold via DB `CHECK` constraints: `step_count BETWEEN 1 AND 6`, `est_minutes BETWEEN 1 AND 12`, `reversible = true`, `needs_tools = false`, named reviewer + review date + manual doc required for `active`.
- `consent_gate` records `gate` (1|2), `answer` (`yes|no|silence|not_asked`), `choice` (`continue_here|switch_to_video|null`), and `not_asked_reason`.
- `fix_attempt` records `outcome` (`worked|not_worked|abandoned|safety_stop`), `steps_done`, `household_report`, and `observed_on_video`.
- `visit_plan`, `plan_hypothesis`, `plan_part`, `assignment_candidate`, `slot_proposal`, `visit_media`, `access_log`, and `identity_merge` are app-output tables (empty in seed CSVs, populated at runtime and by Part B mocks).
- `quote` and `quote_line` store integer `amount_paise` and per-line `payer`; `visit` stores `closure_otp_ref` and `closure_confirmed_at` (never the raw OTP code).
- `appliance_event` is append-only (`deny_mutation` trigger) and drives both the Home Memory timeline and cross-centre `read_shared_history()` views.
- `DATA_DICTIONARY.md` confirms all enum strings and column names that `apps/kw_client` Dart models and `mocks/rest` JSON payloads must match verbatim.

## 5. `keepwell/docs_v1/keepwell_example_queries.sql` (24 Reference Queries)

- **Q1–Q4 (Arrival):** Lookup household via `external_ref` phone hash, appliance via `(brand_id, serial_norm)`, centre brand authority (`proceed`, `return_to_brand_with_reason`, `can_install`, `cannot_install`, `cannot_repair`), and pincode service area.
- **Q5–Q11 (Queue, Gates, Safe-Fix, Overrides):** Console board ordering (`safety` → `urgent` → `standard` → `planned`, then `needed_by`), consent gate funnel counts, active safe-fix ranking (brand/series specific first), `tried_summary`, catalogue health/overdue reviews, resolution mix by trigger, and centre overrides union (`urgency_assessment` + `assignment_candidate`).
- **Q12–Q16 (Dispatch & Parts):** Hard-filtered technician candidates, 3-tier stock ladder (`van` → `centre` → `parts_centre`), nearby parts centres by fill rate and anchor distance, same-day area batching, and 90-day technician FTF rate.
- **Q17–Q21 (Memory & Privacy):** Consent-gated `read_shared_history()`, household-visible `access_log` of cross-centre reads, pgvector experience search, reminder eligibility with monthly cap (default 2), and appliance timeline.
- **Q22–Q24 (Visit & Closure):** Address/phone release logged to `access_log` only once ticket is `booked|scheduled|in_progress|needs_part`, and OTP-only closure for both visit jobs and self-fix tickets.

## 6. `keepwell/docs_v1/CASE_GUIDE.md` & `kb/kw_safe_fix_catalogue.pdf`

- 20 cases span all 4 triggers: 9 WhatsApp messages (`C01, C02, C04, C06, C08, C09, C10, C13, C14`), 6 voice calls (`C03, C05, C11, C12, C15, C16`), 3 brand forwards (`C17, C18, C19`), and 2 retailer handovers (`C07, C20`).
- **Safety cases (`C05` geyser shock, `C15` washer motor smoke):** must skip Gate 1 and Gate 2, show stop-use immediately, and never offer video or self-fix.
- **Urgent cases (`C06` frosted freezer with infant milk at risk, `C12` 18-day repeat washer failure):** `C06` sends protective milk/medicine advice regardless of Gate 1; `C12` triggers `URG-REPEAT-30D` and waives visit fee.
- **Authority failure (`C18` Aerovane warranty forwarded to independent `c_cc`):** returned to brand with reason; never recommends another centre.
- **Out of service area (`C11` Shamshabad 501218):** politely declined without recommending another centre.
- **Cross-centre consent (`C14` denied vs `C19` granted):** UI must visibly respect consent boundaries and show logged cross-centre reads when permitted.
- **Provisional identity & merge (`C09`, `C13`, `C14`):** blurry stickers resolved on video merge provisional appliances into verified ones; parts are not reserved before model confirmation.
- **Non-repair jobs (`C07` AC install, `C08` 3-AC preventive service, `C20` washer install):** skip Gate 1 and Gate 2 completely.
- **Safe-fix catalogue (`KW-SF-01 rev B`):** 14 entries including `SF-WM-DRAINFILTER-WC` (used in C03), `SF-AC-FILTER-AV/ZN`, `SF-AC-DRAINLOOK`, `SF-AC-RESET` (`review_due` — must show overdue badge in console library), `SF-FR-SEAL`, `SF-GY-SWITCH`, `SF-WM-LID`, `SF-ANY-POWER`.
- **Stage Hero (`C03`):** Hindi call to `c_fw`, Wavecrest washer E21, warranty ended 22 days ago, Gate 1 = yes, Gate 2 = switch to video via WhatsApp link, `SF-WM-DRAINFILTER-WC` tried on camera (coins found, E21 returns → `not_worked`), diagnosis re-run shifts probability to pump housing, technician assigned then reassigned in console, estimate → firm quote → approval → UPI/GPay → OTP close.

---

## Open Questions & Environment Observations

1. **Repo Path Layout:** The repo currently has `SHARED_CONTRACT.md` and `keepwell_design_doc.md` at root and the dataset/schema under `keepwell/docs_v1/` (with `keepwell_sim_dataset_v0.2.zip`) rather than `contract/` and `input/`. Logged in `docs/DECISIONS_B.md`; our fixture generator will auto-detect both `input/dataset/` and `keepwell/docs_v1/keepwell_sim_dataset_v0.2.zip`.
2. **Local SDK Availability:** On this machine, `flutter`, `dart`, `melos`, and `firebase` CLI are not yet installed (Homebrew, Node v24.22.2, npm, and Python 3 are available). Installing Flutter SDK + Firebase CLI is required to run `flutter analyze`, `flutter test`, `flutter build web`, and the Firebase emulators.
3. **Google Maps API Key & Looker Studio Embed URL:** Both are optional at dev/demo time; `apps/console` and `apps/brand` will read them via `--dart-define` and provide clean, accessible native fallbacks when absent.

## What We Will Build First

1. **Milestone B0 (Now):** Rules, `docs/NOTES_B.md`, `docs/DECISIONS_B.md`, `docs/design/DESIGN_SPEC.md`, Part B skills/workflows, and the Implementation Plan artifact.
2. **Milestone B2 (`mocks/` first, immediately runnable on Python/Node):** Build `mocks/fixtures/build_fixtures.py` reading the real 55 CSVs + `inbox.json` + `voice_scripts.json`, `mocks/rest/` (FastAPI covering every Contract C5 endpoint with stateful mutations and `X-Mock-Fail`), `mocks/ws/` (WebSocket server replaying C03 per Contract C7), and `mocks/firestore/` (emulator fixtures + C03 real-time time-lapse script).
3. **Milestone B1 → B7 (Flutter monorepo once Flutter SDK is installed):** `apps/kw_ui` + gallery, `apps/kw_client`, `apps/console` (Board, Detail, Live Stage View, Calendar, Overview FVR-14, Stock/Prices/SafeFix/Overrides, Demo Drawer), `apps/household` (WhatsApp Simulator, Call Dialer, Video-Link `/v/<token>`, Home Memory, Quote/GPay/OTP), `apps/field` (Technician offline-first + Parts Centre), `apps/brand`, `infra/frontend/` (`firebase.json`, `firestore.rules`), and Lighthouse/WCAG 2.2 AA verification.
