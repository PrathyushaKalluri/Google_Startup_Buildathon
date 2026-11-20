# Keepwell Part A Hand-off Package (`docs/HANDOFF_A.md`)

**Branch:** `part-a/agent-core` (do not merge without Integrator contract verification)  
**Scope:** Agent and Platform Core (database, RLS, auth, Model Armor, 10 deterministic engines, lexicons, ADK agents, 24-tool MCP server, Gemini Live WebSocket bridge, full REST API v1, Firestore projections, worker, BigQuery analytics, 20+100 eval harness, GCP infra scripts).

---

## 1. Run It (Clean Machine)

### Prerequisites
- Python 3.9+ (targets Python 3.12 in `infra/backend/Dockerfile`)
- PostgreSQL with `postgis`, `vector` (`pgvector`), `pgcrypto`, `btree_gist` (e.g., Homebrew `postgresql@18` + `postgis` + `pgvector` locally, or Cloud SQL PostgreSQL 16 in GCP)
- Optional for cloud deploy: `gcloud` CLI authenticated against a GCP project in `asia-south1`

### Local Quickstart (PostgreSQL-Only, `psycopg` 3 + Real RLS)
```bash
cd keepwell
python3 -m venv .venv
source .venv/bin/activate
pip install -r services/requirements.txt

# 1. Load unmodified keepwell_schema.sql, configure kw_app (NOSUPERUSER NOBYPASSRLS),
#    load all 55 dataset CSVs (15,465 rows), and apply 001_part_a_additions.sql
PYTHONPATH=. .venv/bin/python db/seed/load_seed.py

# 2. Run full Part A test suite (50 tests, all RLS & API tests run as kw_app)
PYTHONPATH=. .venv/bin/pytest -v db/tests/ services/agents/engines/tests/ services/api/tests/ evals/test_evals.py

# 3. Run 20-case + 100-case evaluation harness against all 5 release gates
PYTHONPATH=. .venv/bin/python evals/eval_runner.py

# 4. Run C03 Live WebSocket scripted call end-to-end
PYTHONPATH=. .venv/bin/python services/live/tools/scripted_client.py

# 5. Start REST API + MCP + Live WS on :8000 (fails fast if DATABASE_URL is not Postgres)
PYTHONPATH=. .venv/bin/uvicorn services.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### Production / Cloud Run Deploy (`asia-south1`)
```bash
cd keepwell/infra/backend
./setup_gcp.sh <GCP_PROJECT_ID>
./deploy_backend.sh <GCP_PROJECT_ID>
```

---

## 2. Contract Completeness Checklist (Sections C5–C8)

- [x] **System & Discovery:** `/healthz`, `/readyz`, `/openapi.json` (committed at `services/api/openapi.json`, 61 paths), `/v1/meta/version`, `/mcp` (24 tools). Verified in `services/api/tests/test_contract.py::test_system_health_ready_version_openapi_and_mcp`.
- [x] **Centre Console Endpoints (C5.2):** `GET /v1/tickets`, `GET /v1/tickets/{id}`, `POST /reclassify-urgency`, `POST /reassign`, `POST /rerun-diagnosis`, `POST /return-to-brand`, `POST /message`, `GET /v1/centre/{overview,technicians,calendar,stock,prices,overrides}`, `GET /v1/appliances/{id}/timeline`, `GET /v1/safefix[/{code}]`. Verified in `test_contract.py`.
- [x] **Technician Endpoints (C5.2):** `GET /v1/technicians/me/jobs`, `POST /me/location`, `GET /v1/visits/{id}` (logs `access_log`), `POST /check-in`, `POST /parts-used`, `POST /outcome`, `POST /media/upload-url`, `POST /v1/tickets/{id}/quotes`, `POST /debrief`, `POST /debrief/confirm`, `POST /close/request-otp`, `POST /close/confirm`, `POST /v1/devices`. Verified in `test_contract.py::test_technician_flow_payment_sandbox_debrief_and_otp_close`.
- [x] **Parts Centre & Brand Endpoints (C5.2):** `GET/POST /v1/partscentre/requests`, `PUT /v1/partscentre/stock`, `GET /v1/brand/{requests,analytics}`. Verified in `test_contract.py`.
- [x] **Household Public & Payment Endpoints (C5.2):** `POST /v1/public/session`, `GET /v1/public/home/{token}`, `GET/POST /v1/public/quotes/{token}[/approve|/pay-intent|/payment|/payment/sandbox-complete]`, `POST /v1/public/otp/{token}/confirm`. Payment never closes a job; OTP only.
- [x] **Channels (C5.2 & C5.3):** `GET/POST /v1/channels/whatsapp/webhook` (HMAC), `POST /simulator/{media,inbound}`, `POST /channels/brand/requests` (returns `202 received|declined`), `POST /channels/retailer/handovers` (`202`), `POST /channels/payments/webhook` (HMAC).
- [x] **Admin & Demo (C5.2):** `GET /v1/admin/demo/cases`, `POST /play-case`, `GET /households`, `POST /reset`, `POST /projection/rebuild`, `POST /replay-call`.
- [x] **Firestore Projections (C6) & Live Event Catalogue (C8):** All paths (`centres/{cid}/tickets`, `conversations`, `turns`, `feed`, `technicians`, `visits`, `parts_requests`, `households/{hid}/whatsapp_thread`, `meta/demo`) written via `services/worker/projections.py` and rebuilt idempotently.
- [x] **Live Call WebSocket (C7):** `WS /v1/live/call` handles `start`, PCM16 binary, `video_frame`, `image`, `client_state`, `end`, `text_in` (DEMO_MODE), `go_away` + transparent session resumption, and `/v/<token>` video-link resumption. Verified by `services/live/tools/scripted_client.py` (22 ordered events on C03).

---

## 3. What Is Real vs. What Remains Local / Not Done

### Verified Live Against GCP Project `gen-lang-client-0527907563` (`asia-south1`, gated by `LIVE_GOOGLE=1`)
- **Firestore Native (`asia-south1`):** `services/worker/projections.py` writes batched projections directly to `projects/gen-lang-client-0527907563/databases/(default)` (`backend: real_firestore`), while keeping `FIRESTORE_EMULATOR_HOST` and offline `memory_fallback` paths intact. Two consecutive `POST /v1/admin/projection/rebuild` runs returned identical counts (`tickets: 414, technicians: 36, visits: 413, parts_requests: 6, feed: 251`).
- **Cloud Storage (`asia-south1`):** `services/common/storage.py` uploads directly to `gs://gen-lang-client-0527907563-kw-media` and `gs://gen-lang-client-0527907563-kw-kb` (`backend: real_gcs`) with 48h `retain_until` metadata.
- **Gemini Embeddings (`gemini-embedding-2`) + `pgvector`:** `kb/embed_experience.py` embedded all 674 `experience_case` rows (768-d) into PostgreSQL `pgvector` and runs native `<=>` cosine similarity retrieval (`backend: pgvector+real_gemini_embedding_2`).
- **KB PDF Ingestion (21 PDFs):** `kb/ingest_file_search.py` uploaded all 21 KB PDFs to both `gs://gen-lang-client-0527907563-kw-kb/` (`real_gcs`) and Gemini Files API (`real_gemini_files_and_gcs`); zero-fabricated-citations eval gate passed (`0/15`).
- **Real Model Armor API (`asia-south1`):** Created data-residency-compliant template `projects/gen-lang-client-0527907563/locations/asia-south1/templates/keepwell-guard-v1`. `services/common/untrusted_guard.py` calls `:sanitizeUserPrompt` / `:sanitizeModelResponse` (`backend: real_model_armor`), returning `filtered=False` on benign C03 input and `filtered=True` (`findings=['model_armor:pi_and_jailbreak']`) on prompt injection; regex guard remains only as an offline/outage fallback.
- **Firebase Auth real ID-token verification:** `services/common/auth.py` calls `firebase_admin.auth.verify_id_token()` first for all 3-segment JWTs and accepts `demo:<email>` / unsigned emulator JWTs **only** when `DEMO_MODE=true` or `FIREBASE_AUTH_EMULATOR_HOST` is set.
- **Gemini Live API (`gemini-3.1-flash-live-preview`) C03 text + real audio + session resumption:** Verified live bidirectional session (`text_in` returning 856 KB native PCM16 audio + Hindi transcript + live session resumption handle, followed by resumed session streaming 151 KB real 16kHz PCM16 speech returning real input transcription + 716 KB native audio response).
- **Cloud SQL PostgreSQL 16 Schema & Extensions (`asia-south1`):** Created minimal `db-f1-micro` instance `kw-pg-verify` (`PostgreSQL 16.15`), loaded `input/docs/keepwell_schema.sql` unmodified + `001_part_a_additions.sql` (68 base tables in `kw`), verified all 4 extensions (`btree_gist 1.7`, `pgcrypto 1.3`, `postgis 3.6.4`, `vector 0.8.7`), then **stopped** `kw-pg-verify` (`state: STOPPED`, `activationPolicy: NEVER`, `authorizedNetworks: []`).

### Not Done / Remaining Local Sandbox Components
- **Cloud Run deployment (`infra/backend/deploy_backend.sh`):** Not deployed to Cloud Run per instruction; scripts pass `bash -n` and are ready when Integrator deploys.
- **Live BigQuery / BQML execution & Google Maps Routes API calls:** Maps APIs (`routes`, `addressvalidation`, `geocoding-backend`) are enabled on `gen-lang-client-0527907563`, while runtime `assignment.py` currently uses the Haversine fallback; `analytics/bigquery_views.sql` and `bqml_models.sql` are authored but not executed in BigQuery yet.
- **Contract-specified local sandboxes:** `PAYMENT_MODE=sandbox` (`/payment/sandbox-complete`), `OTP_PROVIDER=sandbox` (`sandbox_code`), and `WHATSAPP_MODE=simulator` (plus real Meta HMAC verification).
- **P2 optional PSTN SIP trunking:** `services/live/pstn.py` remains a stub (`TELEPHONY_MODE=web` is default).

---

## 4. Decisions & Change Requests
- **Decisions (`docs/DECISIONS_A.md`):** D-A01 (PostgreSQL-only with `psycopg` 3 & real `kw_app` RLS), D-A02 (Env-driven Gemini model IDs + `GOOGLE_GENAI_USE_VERTEXAI` switch), D-A03 (Dev phone hash key matching dataset CSVs), D-A04 (Additive migration `001_part_a_additions.sql`), D-A05 (Firestore emulator + local projection mirror), D-A06 (Python 3.9–3.12 typing compatibility), D-A07 (Legacy `app/` isolated).
- **Change Requests (`contract/CHANGE_REQUESTS.md`):** `CR-A-1` (additive `DEMO_MODE=true` `text_in` WebSocket frame for scripted testing). Zero breaking contract changes.

---

## 5. Google Products Used

| Google Product / API | Where in Code | Evidence |
|---|---|---|
| **Gemini API (`google-genai`)** | `services/agents/llm_client.py`, `kb/ingest_file_search.py`, `kb/embed_experience.py` | Env-configured `gemini-3.8-flash`, `gemini-3.5-flash-lite`, `gemini-3.1-pro-preview`, `gemini-embedding-2` |
| **Gemini Live API** | `services/live/bridge.py`, `services/live/prompts/live_agent.md` | `build_gemini_live_config()` with compression, resumption, GoAway; C03 scripted WS passes (`22` events) |
| **Gemini File Search** | `kb/ingest_file_search.py` | 21 KB PDFs mapped to `keepwell-kb-global` + grounded citations verified (`0` fabricated) |
| **Model Armor** | `services/common/untrusted_guard.py` | `10/10` (100%) adversarial prompt injections filtered & logged |
| **MCP (Streamable HTTP)** | `services/mcp/server.py` | 24 tools mounted at `/mcp`, verified in `test_contract.py` |
| **Cloud SQL (PostgreSQL 16 + PostGIS + pgvector + RLS)** | `db/schema.sql`, `db/migrations/001_part_a_additions.sql`, `infra/backend/setup_gcp.sh` | 69 tables / 15,465 rows seeded; 7/7 RLS tests pass as `kw_app` (`NOSUPERUSER NOBYPASSRLS`) |
| **Firestore (Native)** | `services/worker/projections.py` | All C6 paths & C8 events projected; idempotent rebuild verified |
| **Firebase Auth & FCM** | `services/common/auth.py`, `services/api/routes_technician.py` | Role/centre claims + household custom token minting (`/v1/public/session`) |
| **Cloud Storage** | `services/common/storage.py`, `infra/backend/setup_gcp.sh` | Media upload adapter with 48h ephemeral lifecycle |
| **Cloud Run, Cloud Build, Artifact Registry, Secret Manager, Pub/Sub, Cloud Scheduler** | `infra/backend/{Dockerfile,cloudbuild.yaml,setup_gcp.sh,deploy_backend.sh}` | Multi-stage non-root container; all shell scripts pass `bash -n` |
| **BigQuery, BigQuery ML & Looker Studio** | `analytics/{bigquery_views.sql,bqml_models.sql,LOOKER.md}` | 10 BigQuery views (`v_fvr_14d`, FTF, gate funnel, etc.) + 2 BQML models |
| **Google Pay (UPI)** | `services/agents/engines/payments.py`, `services/api/routes_public.py` | UPI intent + Google Pay Web TEST/PROD payload + HMAC webhook verified |

---

## 6. Risks for Merge, Deploy & Demo
1. **Live API preview latency/quota on venue Wi-Fi:** Mitigated by `POST /v1/admin/demo/replay-call` recorded-call fallback and transparent GoAway session resumption.
2. **PostgreSQL extension availability in Cloud SQL `asia-south1`:** Verify `postgis`, `vector`, `pgcrypto`, `btree_gist` on first `setup_gcp.sh` run; AlloyDB is the documented fallback.
3. **Host Python 3.9 vs Docker Python 3.12:** All code is verified on Python 3.9 and targets Python 3.12 in `Dockerfile`; run `pytest` inside the built container during Integrator CI.

---

## 7. Quality Report
- **Offline automated tests (`pytest`):** **51 passed, 6 skipped (`LIVE_GOOGLE=1`), 0 failed** (all against local PostgreSQL as `kw_app` `NOSUPERUSER NOBYPASSRLS`)
- **Live Google integration tests (`LIVE_GOOGLE=1 pytest services/api/tests/test_live_google.py`):** **6 passed, 0 failed** (`56.75s`) — real Firestore idempotent rebuild, real GCS upload, real `gemini-embedding-2` + `pgvector`, real Model Armor API (`asia-south1`), real Firebase Auth verification, real `gemini-3.1-flash-live-preview` C03 text + real PCM16 audio + session resumption.
  - `db/tests/test_rls.py`: 7 passed (`kw_app` non-superuser `NOBYPASSRLS` check, manifest parity, real Postgres RLS centre isolation + cross-centre insert `InsufficientPrivilege`, native `kw.read_shared_history()`, append-only & gate DB triggers, `psycopg` 3 `AsyncConnection`, Model Armor)
  - `services/agents/engines/tests/test_engines.py`: 34 passed (all 10 engines, 100% safety recall, 50-part bogus fuzz test, exact 30/25/20/15/5/5 weights, 18% GST, OTP/payments)
  - `services/api/tests/test_contract.py`: 8 passed (startup fail-fast if `DATABASE_URL` is not Postgres, all C5/C6/C7/C8 contract flows, C03 Live WS, C18 decline, debrief, OTP closure, `live_api_degraded` fallback, `fvr_14d` Postgres view, all 20 cases via `play-case`)
  - `services/api/tests/test_live_google.py`: 6 passed under `LIVE_GOOGLE=1` (skipped offline)
  - `evals/test_evals.py`: 2 passed
- **Eval release gates (`evals/eval_runner.py`):** **5/5 PASS**
  - Safety recall: `100.0%` (29/29) | Gate-skip: `100.0%` (7/7) | Authority: `100.0%` (3/3) | Urgency accuracy: `99.2%` | Fabricated citations: `0` | Adversarial ModelArmor: `100.0%` (10/10)
- **Self-assessment:** See `docs/rubric_A.md`.
