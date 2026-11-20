# KEEPWELL SHARED CONTRACT v1 (frozen)

This file is part of every Keepwell system prompt (Part A, Part B and the Integrator). It is the only thing the two halves share at build time. It is frozen: nobody edits it during the parallel build. If something in it is wrong or missing, write the request in `contract/CHANGE_REQUESTS.md` on your own branch (one entry: what, why, proposed text) and carry on with the most reasonable reading. The Integrator resolves every request.

Where this file and a builder prompt disagree, this file wins. Where this file and `input/dataset/keepwell_schema.sql` disagree on a database name or enum, the schema wins.

---

## 0. The product in one paragraph

Keepwell is a platform that service centres and brands deploy. It is the face of the centre and of the brand, never of the household, and it never recommends or matches a centre. One agent answers four triggers for the centre whose line or integration was used: (1) household call, (2) household message (WhatsApp, app, centre console), (3) brand-forwarded request, (4) retailer handover. For every repair it identifies the household and appliance, checks the centre's authority for the brand, assesses urgency itself (the household is never asked "how urgent"), asks clarifying questions, and asks two consent questions before any self-fix: gate 1 "okay to try a safe fix?" and, only after yes, gate 2 "switch to video, or carry on here?" (silence counts as no; safety cases skip both; non-repair jobs get neither). It guides one catalogued safe fix at a time, records what was tried, re-runs diagnosis if the fix fails, then books the centre's own technician with everything already known (technician chosen by fix confidence 30, parts readiness 25, time to visit 20, route cost 15, reliability 5, household fit 5; price is not scored). Quote goes estimate, then firm, then approval. Closure is by the household's OTP only. The centre can reassign or reclassify from its console; that is logged as a training signal.

The full reasoning is in `input/docs/keepwell_design_doc.md`. The data model is `input/dataset/keepwell_schema.sql` (v0.2, 63 tables). The seeded world and the 20 test cases are in `input/dataset/` (read its README first).

Priority tiers used in both prompts:

- **P0** is the stage scenario end to end (C03: Hindi call, washer E21, consent gates, switch to video, failed drain-filter fix, re-run, assignment, reassignment, quote, OTP close) plus all four triggers working on the seeded cases.
- **P1** is everything else in the design doc's prototype scope and the full 20-case set.
- **P2** is stretch: technician copilot on Live API, Route Optimization API, parts-centre ranking, Fleet Engine live arrival, BigQuery ML.

---

## 1. Frozen technical decisions

| Area | Decision |
|---|---|
| Cloud project | One Google Cloud project, region `asia-south1` (Mumbai) for everything that holds personal data. Live API may be served from a different location if the model is not available in India; document it. |
| Backend language | Python 3.12, FastAPI, `uvicorn`, Pydantic v2, SQLAlchemy 2 + `psycopg` 3 (async) |
| Agents | Google Agent Development Kit (`google-adk`) for all agents; Gemini API through `google-genai` |
| Tools protocol | MCP (Streamable HTTP) server mounted at `/mcp` inside the API service; ADK agents and the Live agent call tools through it or through the same Python functions it wraps |
| Database | Cloud SQL for PostgreSQL 16 with PostGIS, pgvector, pgcrypto, btree_gist (AlloyDB for PostgreSQL is the fallback). Schema is `input/dataset/keepwell_schema.sql`, unmodified except by additive migrations in `db/migrations/` |
| Live state | Firestore (Native mode), written only by the backend, read by the apps (section 6) |
| Files | Cloud Storage, India region; originals of KB documents, call recordings, photos, video frames (with consent) |
| Analytics | BigQuery, fed from Postgres through scheduled export; Looker Studio for dashboards |
| Front ends | Flutter 3.x (stable), Dart 3.x, Material 3 Expressive, one melos monorepo. Web is the primary target; technician app also builds for Android |
| Front-end data | Firebase Auth (Google sign-in plus email link), Firestore listeners, REST (section 5), FCM for push, Firebase App Check, Firebase Hosting |
| Deploy | Cloud Run (`kw-api`, `kw-worker`), Firebase Hosting (four web apps), Cloud Build, Artifact Registry, Secret Manager, Cloud Scheduler, Cloud Tasks, Pub/Sub |
| Time and money | ISO 8601 with offset (`+05:30` for display, UTC on the wire); money in paise (integers); ids are UUID strings; languages are BCP 47 (`en`, `hi`, `te`) |
| Naming | JSON keys and enum values are the snake_case names in the schema. Dart models use camelCase fields with `json_serializable` snake_case mapping |
| Package/service names | Cloud Run services `kw-api`, `kw-worker`; Firebase hosting targets `console`, `field`, `household`, `brand` |

Model IDs change often. Both halves read model names from environment variables (section 4) and never hard-code them. Defaults at the time of writing (verify against https://ai.google.dev/gemini-api/docs/models on the first day):

- Reasoning agents: `gemini-3.8-flash` (fallback `gemini-3.7-flash`); hard diagnosis may use `gemini-3.1-pro-preview`
- Fast intake and classification: `gemini-3.5-flash-lite`
- Live voice and video: `gemini-3.1-flash-live-preview` (fallback `gemini-2.5-flash-native-audio-preview-12-2025`; on Vertex/Agent Platform `gemini-live-2.5-flash-native-audio`)
- Speech to text for voice notes: Gemini audio understanding or `gemini-3.5-transcribe`
- Text to speech for spoken replies: `gemini-3.1-flash-tts-preview`
- Embeddings: `gemini-embedding-2`, 768 dimensions
- File Search: Gemini API File Search stores (not usable inside the Live API; the Live agent reaches the knowledge base through its own `search_manuals` tool)

---

## 2. Repository and ownership

One repository, `keepwell/`. Three branches: `main` (Integrator), `part-a/agent-core`, `part-b/experience`. Both part branches start from the same commit `contract-v1` that contains only `contract/`, `input/` and empty folders. Folders are owned by exactly one party. Nobody edits a folder they do not own; that is what makes the merge conflict-free.

```
keepwell/
  contract/                 FROZEN. This file, CHANGE_REQUESTS.md
  input/                    READ-ONLY inputs: dataset/ (csv, inbox, kb, evaluator_only), docs/ (design doc, schema, queries, dictionary)
  --- Part A owns ---
  db/                       schema copy, migrations, seed loader, RLS tests
  services/api/             FastAPI app: REST, WebSocket, webhooks
  services/agents/          ADK agents, the engines (safe-fix, urgency, authority, assignment, pricing, parts, gates, OTP, payments) and lexicon/ (repair vocabulary, hazard lexicon)
  services/mcp/             MCP tool server
  services/live/            Live API bridge, call transports, video-link handling
  services/worker/          Cloud Tasks and Scheduler handlers, reminders, projections
  services/common/          config, auth, RLS session, logging, Model Armor guard
  kb/                       File Search ingestion, embedding jobs
  analytics/                BigQuery SQL, BQML, Looker Studio views
  evals/                    gold cases, eval runner, release gates
  infra/backend/            Dockerfile, cloudbuild, Cloud Run, Cloud SQL, Pub/Sub, Scheduler, Secret Manager scripts
  .agents/part-a/           skills and workflows for Part A
  --- Part B owns ---
  apps/kw_ui/               Flutter design-system package
  apps/kw_client/           Dart package: API client, models, Firestore repositories, auth
  apps/console/             Flutter web: centre console, Live Stage view
  apps/field/               Flutter: technician and parts-centre apps (role-based shells)
  apps/household/           Flutter web: WhatsApp simulator, call dialer, video-link page, Home Memory, quote approval
  apps/brand/               Flutter web: brand and retailer portal
  mocks/                    mock REST server, mock WebSocket call server, Firestore emulator fixtures
  infra/frontend/           firebase.json, firestore.rules, hosting targets, App Check
  docs/design/              design spec, motion spec, accessibility checklist, screenshots
  .agents/part-b/           skills and workflows for Part B
  --- Integrator owns ---
  README.md, Makefile, .env.example, docker-compose.yml, .github or cloudbuild root config, docs/, e2e/, deploy/
```

Both parts may add skills under their own `.agents/part-x/` folder. The Integrator moves them into `.agents/` at merge.

---

## 3. Demo world and identities

Nine centres exist with fixed keys. Their UUIDs, lines and WhatsApp numbers are in `input/dataset/csv/service_centre.csv` and `centre_channel.csv`.

| key | centre | brands (authority) |
|---|---|---|
| `c_av` | Aerovane Authorised Service, Gachibowli | Aerovane (authorised) |
| `c_zn` | Zenith Care Hub, Kondapur | Zenith (authorised) |
| `c_fw` | Frost and Wave Service Point, Kukatpally | Frostline, Wavecrest (authorised) |
| `c_cc` | Cool Craft Appliance Services, Madhapur | Aerovane, Frostline, Wavecrest, Zenith (independent) |
| `c_aq` | AquaCare RO and Geyser Services, Manikonda | Heatwell, Purelo (authorised) |
| `c_mh` | Metro Home Appliance Care, Miyapur | five brands (independent) |
| `c_ip` | InstallPro Mounting Services, Tolichowki | Aerovane, Zenith (installation only) |
| `c_ls` | Lakeshore Service Centre, Jubilee Hills | Wavecrest (authorised), others independent |
| `c_hw` | Heatwell Authorised Service, Banjara Hills | Heatwell (authorised) |

**Demo users** (created by Part A in Firebase Auth for the real project, and by Part B in the Auth emulator for local work), one per role per centre, password-less in the emulator:

`console.<key>@keepwell.demo` (role `centre_admin`), `tech1.<key>@keepwell.demo`, `tech2.<key>@keepwell.demo` (role `technician`, bound to the first and second technician of that centre by `technician.csv` order), `parts.demo@keepwell.demo` (role `parts_centre`), `brand.<brand_key>@keepwell.demo` (role `brand`), `platform@keepwell.demo` (role `platform`).

**Custom claims on the Firebase ID token:** `role` in (`centre_admin`, `technician`, `parts_centre`, `brand`, `platform`), `centre_id` (UUID, absent for brand and platform), `technician_id` (technicians only), `parts_centre_id`, `brand_id`.

**Backend rule:** the API verifies the ID token on every request, opens one transaction, and runs `SET LOCAL kw.centre_id = '<claim>'` (or `SET LOCAL kw.role = 'platform'` for platform jobs and the call agent's cross-centre functions). The API connects as role `kw_app`. A centre never sees another centre's rows; that is tested.

**Public surfaces without sign-in:** households are identified by their call or message, so household pages use signed, expiring tokens (magic links), never accounts. Brand and retailer systems use an API key header `X-Keepwell-Key` that maps to a brand or retailer.

---

## 4. Environment variables (names are frozen)

```
GCP_PROJECT_ID, GCP_REGION=asia-south1
DATABASE_URL                       postgresql+psycopg://kw_app:...@/keepwell?host=/cloudsql/<instance>
FIREBASE_PROJECT_ID, FIRESTORE_EMULATOR_HOST (dev), FIREBASE_AUTH_EMULATOR_HOST (dev)
GEMINI_API_KEY                     (or Vertex/Agent Platform credentials when GOOGLE_GENAI_USE_VERTEXAI=true)
GEMINI_MODEL_AGENT, GEMINI_MODEL_FAST, GEMINI_MODEL_PRO, GEMINI_MODEL_LIVE, GEMINI_MODEL_EMBED, GEMINI_MODEL_TTS, GEMINI_MODEL_STT
FILE_SEARCH_STORE_PREFIX=keepwell-kb
GOOGLE_MAPS_API_KEY                (Routes, Geocoding, Address Validation, Places)
WHATSAPP_VERIFY_TOKEN, WHATSAPP_APP_SECRET, WHATSAPP_ACCESS_TOKEN, WHATSAPP_MODE=simulator|live
TELEPHONY_MODE=web|pstn, TELEPHONY_PROVIDER_*   (optional PSTN bridge)
MAGIC_LINK_SIGNING_KEY, PHONE_HASH_KEY, OTP_PROVIDER=sandbox|live
PAYMENT_MODE=sandbox|live, PAYMENT_WEBHOOK_SECRET, UPI_VPA, GOOGLE_PAY_ENVIRONMENT=TEST|PRODUCTION, GOOGLE_PAY_MERCHANT_ID, GOOGLE_PAY_GATEWAY, GOOGLE_PAY_GATEWAY_MERCHANT_ID
MODEL_ARMOR_TEMPLATE, GCS_BUCKET_MEDIA, GCS_BUCKET_KB
API_BASE_URL (used by apps), LIVE_WS_URL, DEMO_MODE=true|false
```

Secrets go in Secret Manager, never in the repo. `.env.example` is written by the Integrator from this list.

---

## 5. REST API v1 (Part A implements, Part B consumes)

Base path `/v1`. JSON. `Authorization: Bearer <Firebase ID token>` unless marked **public** (signed token in the path) or **key** (X-Keepwell-Key). Errors are always `{ "error": { "code": "snake_case", "message": "human text", "field": null, "request_id": "..." } }` with the usual HTTP status. Lists return `{ "items": [...], "next_cursor": null }`. Writes accept an `Idempotency-Key` header. Part A also serves `/openapi.json`, `/healthz`, `/readyz`, `/v1/meta/version`.

### 5.1 Core objects (field names are database column names)

```
TicketCard      { id, centre_id, trigger, channel, job_type, status, resolution, urgency_class, needed_by,
                  safety_flag, safety_reason, entitlement, household: HouseholdRef, appliance: ApplianceRef|null,
                  complaint_summary, language, created_at, updated_at, flags: [string] }
HouseholdRef    { id, display_name, language, pincode, locality, address_line, verified_via, linked_centres_count }
ApplianceRef    { id, brand, category_code, model_code|null, serial_masked|null, identity_status, purchase_date|null, warranty_end|null }
TicketDetail    { card: TicketCard, case_card: CaseCard, urgency: UrgencyAssessment[], gates: ConsentGate[], clarifying_qa: QA[],
                  fix_attempts: FixAttempt[], tried_summary: object[], diagnosis: Diagnosis|null, visit_plan: VisitPlan|null,
                  candidates: AssignmentCandidate[], slot_proposals: SlotProposal[], quotes: Quote[], payments: PaymentIntent[], debrief: Debrief|null, visit: Visit|null,
                  timeline: TimelineEvent[], authority: { level, decision } }
CaseCard        { summary, symptoms[], error_codes[], what_was_tried[], safety_notes, identity_notes, sources: [Citation] }
UrgencyAssessment { class, rule_codes[], facts, assessed_by (agent|centre_console), reason, protective_steps_sent, created_at }
ConsentGate     { gate (1|2), asked_at, answer (yes|no|silence|not_asked), choice (continue_here|switch_to_video|null), not_asked_reason }
FixAttempt      { id, catalogue_code, title, offered_at, steps_done, of, outcome (worked|not_worked|abandoned|safety_stop), household_report, observed_on_video }
Diagnosis       { hypotheses: [{ fault_key, label, probability, evidence[], citations: [Citation] }], abstained: bool, reason|null, rerun_of|null, model_version }
Citation        { doc_title, page|null, uri|null, snippet }
VisitPlan       { id, version, trigger_reason, already_tried[], required_skills[], est_duration_p50_min, est_duration_p80_min, tools_needed[],
                  requires_safety_cert[], parts: [{ part_no, name, probability, quantity, source_ladder: van|centre|parts_centre, ready: bool }], access_notes, confidence }
AssignmentCandidate { technician_id, name, rank, score, score_breakdown: { fix_confidence, parts_readiness, time_to_visit, route_cost, reliability, household_fit },
                  slot_start, slot_end, outcome (proposed|chosen|not_chosen), chosen_by, override_reason|null, why: string }
SlotProposal    { slot_start, slot_end, price_low_paise, price_high_paise, shown_at, accepted }
Quote           { id, version, quote_type (estimate|firm), lines: [{ kind, description, amount_paise, payer }], total_paise, household_paise, covered_paise, approved_at|null, approval_method|null }
Debrief         { id, visit_id, status (processing|ready|confirmed), language, transcript, extracted: { fault_found, work_done,
                  parts_used: [{ part_no, quantity }], advice_for_household, appliance_notes, follow_up_needed: bool },
                  unresolved: [string], confirmed_at|null }
PaymentIntent   { id, quote_id, amount_paise, status (created|pending|paid|failed|expired), method (upi_intent|google_pay),
                  upi_intent_url|null, google_pay: { environment (TEST|PRODUCTION), merchant_name, merchant_id, gateway, gateway_merchant_id,
                  transaction_info: { currency_code: "INR", total_price_status: "FINAL", total_price: "<rupees, 2 dp>" } }|null,
                  payment_ref|null, created_at, expires_at, paid_at|null }
Visit           { id, technician_id, planned_start, planned_end, check_in_at, check_out_at, outcome, closure_confirmed_at, rating }
TimelineEvent   { at, type, actor (agent|household|centre|technician|brand|retailer|system), title, detail, ref }
```

### 5.2 Endpoints

**Centre console (role `centre_admin`, `platform`)**

| Method and path | Purpose | Returns |
|---|---|---|
| `GET /tickets?status=&urgency_class=&trigger=&q=&cursor=` | The case board, ordered safety, urgent, standard, planned, then needed_by | list of `TicketCard` |
| `GET /tickets/{id}` | Everything about one case | `TicketDetail` |
| `POST /tickets/{id}/reclassify-urgency` `{class, reason}` | Centre disagrees with the agent; stored as `assessed_by=centre_console` | `TicketDetail` |
| `POST /tickets/{id}/reassign` `{technician_id, slot_start, slot_end, reason}` | Reassign; logged as override | `TicketDetail` |
| `POST /tickets/{id}/rerun-diagnosis` | Run the diagnosis and visit plan again | `TicketDetail` |
| `POST /tickets/{id}/return-to-brand` `{reason}` | When authority fails | `TicketDetail` |
| `POST /tickets/{id}/message` `{text}` | Centre message to the household on their channel | `TimelineEvent` |
| `GET /centre/overview` | KPIs: open by class, first-time fix, `fvr_14d`, self-fix resolution, gate funnel, jobs per technician-day (definitions in section 11) | object |
| `GET /centre/technicians`, `GET /centre/calendar?date=` | People and day plan | lists |
| `GET /centre/stock`, `GET /centre/prices` | Private to the centre | lists |
| `GET /centre/overrides` | Reclassifications and reassignments (training signal) | list |
| `GET /appliances/{id}/timeline` | Technical history, via `read_shared_history` (logs cross-centre reads) | `TimelineEvent[]` |
| `GET /safefix`, `GET /safefix/{code}` | Catalogue with effectiveness | list, object |

**Technician (role `technician`)**

| Method and path | Purpose |
|---|---|
| `GET /technicians/me/jobs?date=` | The day's visits |
| `GET /visits/{id}` | Brief: plan, already tried, parts and where they are, access notes; address and phone only once the slot is confirmed (each read is logged) |
| `POST /visits/{id}/check-in` `{lat, lon}` ; `POST /visits/{id}/parts-used` ; `POST /visits/{id}/outcome` ; `POST /visits/{id}/media/upload-url` |
| `POST /tickets/{id}/quotes` `{lines[]}` | Firm quote after inspection; variance against the estimate is computed |
| `POST /visits/{id}/debrief` `{media_ref, language}` (spoken close-out note uploaded first through `media/upload-url`) returns `Debrief`; `POST /visits/{id}/debrief/confirm` `{extracted}` lets the technician confirm or correct what the agent heard; confirmed content updates the appliance timeline |
| `POST /visits/{id}/close/request-otp` ; `POST /visits/{id}/close/confirm` `{otp_ref, code}` | Closure by the household's OTP only |
| `POST /technicians/me/location` `{lat, lon, at}` | Position for the centre board |

**Parts centre (role `parts_centre`)**: `GET /partscentre/requests`, `POST /partscentre/requests/{id}/accept|ready|handover`, `PUT /partscentre/stock`.

**Brand and retailer (role `brand` or key)**: `GET /brand/requests`, `GET /brand/analytics` (installed base, service quality), and the key-authenticated intake in 5.3.

**Household (public, signed token in the path)**: `GET /public/home/{token}` (Home Memory: appliances, timeline, next due, warranty), `GET /public/quotes/{token}`, `POST /public/quotes/{token}/approve`, `POST /public/otp/{token}/confirm`, and payment: `POST /public/quotes/{token}/pay-intent` `{method}` returns `PaymentIntent`; `GET /public/quotes/{token}/payment` returns the latest `PaymentIntent`; `POST /public/quotes/{token}/payment/sandbox-complete` `{payment_id, result: success|failure}` exists only when `PAYMENT_MODE=sandbox`. The provider's callback is `POST /channels/payments/webhook` (HMAC with `PAYMENT_WEBHOOK_SECRET`), which marks the intent and the household `settlement_line` paid and writes `payment_ref`. Payment never closes a job; only the OTP does.

Household session for live data: `POST /public/session` `{magic_token}` returns `{ firebase_custom_token, household_id, expires_at }`; the household apps sign in with that custom token (claim `household_id`) to read their `whatsapp_thread` from Firestore. Tokens are signed, expiring and scoped to one household.

**Channels**

| Method and path | Purpose |
|---|---|
| `GET/POST /channels/whatsapp/webhook` | Meta Cloud API webhook (verify and inbound). HMAC checked |
| `POST /channels/whatsapp/simulator/inbound` `{to_number, from_phone, sender_profile_name, messages: [WaMessage]}` | Same pipeline, used by the household simulator. `WaMessage` is exactly the message shape in `input/dataset/inbox/inbox.json` (`type` text, audio, image, location, with media uploaded first via `POST /channels/whatsapp/simulator/media`) |
| `POST /channels/brand/requests` (key) | Brand forward; body is the `payload` object of a brand case in `inbox.json` |
| `POST /channels/retailer/handovers` (key) | Retailer handover; body is the `payload` of a retailer case |
| `WS /live/call` | Voice and video call with the agent (section 7) |

**Admin and demo (role `platform`, or `DEMO_MODE=true`)**

| Method and path | Purpose |
|---|---|
| `GET /admin/demo/cases` | The 20 cases with trigger, centre, channel, and `stage_candidate` |
| `POST /admin/demo/play-case` `{case_id}` | Feeds that case's `inbox.json` event through the real pipeline for its receiving centre |
| `GET /admin/demo/households?centre_key=` | Seeded households a presenter can impersonate: `{ household_id, display_name, phone_masked, language, magic_token }` |
| `POST /admin/demo/reset` | Reloads the seed and clears app-output tables and projections |
| `POST /admin/projection/rebuild` | Rebuilds Firestore from Postgres |

Pagination is cursor based. Rate limits return `429` with `Retry-After`.

### 5.3 Brand and retailer payloads

Exactly the `payload` objects in `input/dataset/inbox/brand_requests/*.json` and `retailer_handovers/*.json`. Response: `202 { "ticket_id": "...", "status": "received" | "declined", "declined_reason": null }`. A brand request to a centre that lacks authority is accepted, answered with `declined` and the reason, and returned to the brand.

---

## 6. Live state in Firestore (Part A writes, Part B reads; clients never write)

Everything the apps show live is a projection of Postgres, rebuilt on demand. Document ids are the Postgres UUIDs. Timestamps are Firestore `Timestamp`.

```
centres/{centre_id}
  tickets/{ticket_id}                 TicketCard fields + { unread: bool, last_event_at, assignee: {technician_id, name}|null, next_action: string, payment_status: created|pending|paid|failed|none }
  conversations/{conversation_id}     { ticket_id|null, channel, modality (voice|text|video), language, started_at, ended_at|null,
                                        recording_notice_logged: bool, state: ringing|active|switching_to_video|ended, caller_masked }
    turns/{turn_id}                   { at, speaker (household|agent), text, lang, final: bool, kind: speech|text|image|tool_note }
  feed/{event_id}                     live events, section 8 (the Stage view and the console activity strip read this)
  technicians/{technician_id}         { name, status (available|travelling|on_job|off), current_visit_id|null, last_location: GeoPoint|null, last_ping_at }
  visits/{visit_id}                   { ticket_id, technician_id, planned_start, planned_end, status, brief: VisitPlan-lite, address_released: bool }
  parts_requests/{id}                 { visit_id, part_no, quantity, status (requested|accepted|ready|handed_over), parts_centre_id }
households/{household_id}/whatsapp_thread/{message_id}   { direction (in|out), type, text|null, media_url|null, template|null, at, ticket_id|null, status }
meta/demo                             { active_case_id|null, reset_at }
```

Security rules (Part B writes `firestore.rules`): a signed-in user reads `centres/{cid}/**` only when `request.auth.token.centre_id == cid` or `role == 'platform'`; technicians read only their own `technicians/{id}` and `visits` where `technician_id` matches; `households/**` is readable only by a custom token minted by the demo household session (claim `household_id`); nobody writes from a client. Offline: Firestore persistence on for the field app.

---

## 7. Live call protocol (`WS /v1/live/call`)

Part A hosts it and bridges to the Gemini Live API. Part B's household dialer and video-link page, and the console's test-call button, are its clients. Auth: query `?token=<Firebase ID token | demo household token>`.

Client to server:

```
text frame  {"type":"start","centre_key":"c_fw","caller_number":"+91 50971 16577","language_hint":null,"resume_conversation_id":null}
binary      raw PCM16 little-endian, 16 kHz, mono, 20 to 100 ms chunks (microphone)
text frame  {"type":"video_frame","mime":"image/jpeg","data":"<base64>","ts":1234}     about 1 frame per second, max 640 px long edge
text frame  {"type":"image","mime":"image/jpeg","data":"<base64>","caption":"sticker"}  a still the agent should read (sticker, display)
text frame  {"type":"client_state","modality":"voice|video","muted":false}
text frame  {"type":"end"}
```

Server to client:

```
binary      raw PCM16, 24 kHz, mono (agent voice)
{"type":"ready","conversation_id":"...","session_id":"...","centre_name":"...","recording_notice":"..."}
{"type":"transcript","speaker":"agent|household","text":"...","final":true,"lang":"hi"}
{"type":"video_link","url":"https://<household-host>/v/<token>","expires_at":"..."}
{"type":"modality","value":"video"}                       sent when the same conversation continues on video
{"type":"ui_hint","kind":"show_sticker|show_display|show_drain_filter|hold_steady","text":"..."}   prompts the camera UI
{"type":"event", ...}                                       a live event from section 8, mirrored for the client that wants it
{"type":"go_away","seconds":30}                             Live API session about to be rotated; the server resumes transparently
{"type":"ended","reason":"completed|household_left|timeout|error","ticket_id":"..."}
{"type":"error","code":"...","message":"..."}
```

The video link opens `apps/household` at `/v/<token>`. That page asks for the camera, connects to the same WebSocket with `resume_conversation_id`, sets `client_state.modality=video`, and the server answers `modality: video`. Session limits (audio only 15 min, audio plus video 2 min without compression) are handled by Part A with context-window compression and session resumption; the client never notices.

The PSTN path (a real phone calling the centre's line) is an adapter inside Part A (`TELEPHONY_MODE=pstn`) behind the same internal interface. Web mode must always work, and is the demo default.

---

## 8. Live event catalogue (documents in `centres/{cid}/feed`)

Every event: `{ id, at, centre_id, ticket_id|null, conversation_id|null, type, actor, title, detail, payload }`. `title` is a short human sentence the console prints as is.

`conversation_started` (channel, caller_masked), `recording_notice_logged`, `household_identified` (household_id, verified_via, known_to_this_centre), `appliance_identified` (appliance_id, brand, model, serial_masked, source: sticker|invoice|carton|record), `authority_checked` (level, decision), `urgency_assessed` (class, rule_codes, reason), `safety_stop_sent`, `clarifying_asked` (seq, question), `clarifying_answered`, `gate_asked` (gate), `gate_answered` (gate, answer, choice), `modality_changed` (from, to), `fix_offered` (code, title, steps, est_minutes), `fix_step` (n, of), `fix_result` (outcome, household_report), `diagnosis_updated` (top hypothesis, probability, rerun: bool, evidence), `visit_plan_ready` (already_tried), `candidates_scored` (top 3 with score_breakdown), `slots_offered` (window, price range), `technician_assigned` (name, slot, chosen_by), `reassigned` (from, to, reason), `quote_issued` (type, total_paise), `quote_approved`, `payment_initiated` (method, amount_paise), `payment_confirmed` (payment_ref), `payment_failed` (reason), `debrief_processed` (unresolved count), `otp_sent`, `ticket_closed` (resolution), `brand_request_received`, `brand_request_declined` (reason), `retailer_handover_received`, `shared_history_read` (owner_centre, consent), `error_notice`.

Part B renders a distinct, accessible treatment for each type and falls back to a generic row for unknown types.

---

## 9. Copy and language rules (both halves)

- The household-facing wording the agent emits (consent questions, stop-use messages, recording notice) is produced by Part A and displayed verbatim by Part B. Part B never rewrites agent text.
- Canonical English meanings that must survive translation into Hindi and Telugu: recording notice ("this call may be recorded to help your service centre"); gate 1 ("Are you okay to try a quick, safe fix yourself first?"); gate 2 ("Would you like to switch to video, or carry on here?"); safety stop ("Please stop using it and switch it off at the wall. A technician will come as soon as possible.").
- Tone: calm, specific, no jargon, no blame, never "AI-powered" marketing language. Keepwell speaks in the centre's name.
- UI chrome strings (buttons, labels) are Part B's: English, Hindi, Telugu, through Flutter `intl` ARB files. Numbers and dates use `en-IN` formats.

---

## 10. Definition of done for the interface

A half is "contract complete" when:

- **Part A:** `/openapi.json` validates; every endpoint in section 5 exists and returns the shapes above on the seeded data; every Firestore path in section 6 is written; every event in section 8 is emitted in the C03 run; the WebSocket in section 7 handles a scripted client; contract tests pass.
- **Part B:** every screen runs against `mocks/` (mock REST built from section 5, mock WebSocket, Firestore emulator fixtures built from section 6 using the dataset), and switching `API_BASE_URL`, `LIVE_WS_URL` and the Firebase project to the real ones is configuration only.

The Integrator proves both with consumer-driven contract tests before the first end-to-end run.

---

## 11. Invariants and metric definitions (both halves)

**Parts are never invented.** Every part named in a visit plan, technician brief, debrief, quote, stock request or message must exist in `part_catalogue` for the appliance's brand and be linked to the appliance's model in `part_compatibility`. Part numbers come only from a catalogue lookup tool, never from a model's free text. A part that cannot be matched is listed in `unresolved` or flagged `compatibility_unverified`, and it never appears in a quote. Part B shows unmatched parts as "needs checking", never as a normal line.

**Safety path (our wording for what the old prototype called escalation).** A case classified `safety` skips both consent gates, sends the stop-use instruction at once, goes to the top of the board with a distinct treatment and an audible or push alert, and is assigned the nearest qualified technician. The agent acts on this itself; the centre can reclassify afterwards. No self-fix is ever offered.

**Metrics.** Both halves use these definitions; Part A computes them, Part B labels them identically.

| Metric | Definition |
|---|---|
| First-time fix (FTF) | Existing view `first_visit_outcome`: the first visit ended `fixed` and the ticket had no other visit. Repair jobs only |
| FVR-14 (first-visit resolution, 14 days) | A repair ticket whose first visit ended `fixed`, was closed by OTP, and has no new repair ticket for the same appliance and the same fault family within 14 days of closure. Shown as a gauge on the console overview and the brand portal |
| Self-fix resolution | Share of repair tickets where a catalogue self-fix ended `worked` and no visit was needed |
| Gate funnel | Repair tickets where gate 1 was asked, then yes, then gate 2 asked, then `switch_to_video` |
| Urgency agreement | Share of tickets whose agent-set urgency class was not changed by the centre |
| Override rate | Reassignments and reclassifications per 100 assigned tickets |
| Parts ready at visit | Share of visits where every part in the plan was available at the planned source when the visit started |
