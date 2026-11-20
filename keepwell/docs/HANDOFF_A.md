# Keepwell Part A Hand-off Package (`docs/HANDOFF_A.md`)

**Branch:** `part-a/agent-core` (do not merge without Integrator contract verification)  
**Scope:** Agent and Platform Core (database, RLS, auth, Model Armor, 10 deterministic engines, lexicons, ADK agents, 24-tool MCP server, Gemini Live WebSocket bridge, full REST API v1, Firestore projections, worker, BigQuery analytics, 20+100 eval harness, GCP infra scripts).

---

## 1. Run It (Clean Machine)

### Prerequisites
- Python 3.9+ (targets Python 3.12 in `infra/backend/Dockerfile`)
- Optional for local Postgres/Emulators: Docker + Firebase CLI
- Optional for cloud deploy: `gcloud` CLI authenticated against a GCP project in `asia-south1`

### Local Quickstart (Zero-Docker Parity Mode)
```bash
cd keepwell
python3 -m venv .venv
source .venv/bin/activate
pip install -r services/requirements.txt

# 1. Load all 55 dataset CSVs (15,465 rows) + Part A additive tables & triggers
PYTHONPATH=. .venv/bin/python db/seed/load_seed.py

# 2. Run full Part A test suite (47 tests)
PYTHONPATH=. .venv/bin/pytest -v db/tests/ services/agents/engines/tests/ services/api/tests/ evals/test_evals.py

# 3. Run 20-case + 100-case evaluation harness against all 5 release gates
PYTHONPATH=. .venv/bin/python evals/eval_runner.py

# 4. Run C03 Live WebSocket scripted call end-to-end
PYTHONPATH=. .venv/bin/python services/live/tools/scripted_client.py

# 5. Start REST API + MCP + Live WS on :8000
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

## 3. What Is Not Done (Honest List)
- **Live cloud deployment on a scratch GCP project (A7 stretch):** `gcloud`, `docker`, and `firebase` CLIs are not installed on this host machine. All deployment scripts (`infra/backend/setup_gcp.sh`, `deploy_backend.sh`, `teardown.sh`, `Dockerfile`, `cloudbuild.yaml`, `docker-compose.dev.yml`) are written, syntax-checked (`bash -n`), and ready for the Integrator to execute in GCP.
- **Live Gemini File Search PDF upload & pgvector batch embedding against live API:** Implemented in `kb/ingest_file_search.py` and `kb/embed_experience.py` with local deterministic fallbacks; live network upload is left to deploy time to keep local runs fast and deterministic.
- **P2 stretch items:** Live PSTN SIP trunking (`services/live/pstn.py` holds the adapter interface), Google Maps Route Optimization API live calls (Haversine fallback implemented in `assignment.py`), and running BQML training jobs in BigQuery (`analytics/bqml_models.sql` authored and ready).

---

## 4. Decisions & Change Requests
- **Decisions (`docs/DECISIONS_A.md`):** D-A01 (Dual Postgres 16 + SQLite RLS parity engine), D-A02 (Env-driven Gemini model IDs + `GOOGLE_GENAI_USE_VERTEXAI` switch), D-A03 (Dev phone hash key matching dataset CSVs), D-A04 (Additive migration `001_part_a_additions.sql`), D-A05 (Firestore emulator + local projection mirror), D-A06 (Python 3.9–3.12 typing compatibility), D-A07 (Legacy `app/` isolated).
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
| **Cloud SQL (PostgreSQL 16 + PostGIS + pgvector + RLS)** | `db/schema.sql`, `db/migrations/001_part_a_additions.sql`, `infra/backend/setup_gcp.sh` | 69 tables / 15,465 rows seeded; 5/5 RLS tests pass |
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
- **Total automated tests:** **47 passed, 0 failed** (`1.45s`)
  - `db/tests/test_rls.py`: 5 passed (manifest parity, RLS isolation, consent-gated `read_shared_history()`, append-only & gate DB triggers, Model Armor)
  - `services/agents/engines/tests/test_engines.py`: 34 passed (all 10 engines, 100% safety recall, 50-part bogus fuzz test, exact 30/25/20/15/5/5 weights, 18% GST, OTP/payments)
  - `services/api/tests/test_contract.py`: 6 passed (all C5/C6/C7/C8 contract flows + C03 Live WS + C18 decline + debrief + OTP closure)
  - `evals/test_evals.py`: 2 passed
- **Eval release gates (`evals/eval_runner.py`):** **5/5 PASS**
  - Safety recall: `100.0%` (29/29) | Gate-skip: `100.0%` (7/7) | Authority: `100.0%` (3/3) | Urgency accuracy: `99.2%` | Fabricated citations: `0` | Adversarial ModelArmor: `100.0%` (10/10)
- **Self-assessment:** See `docs/rubric_A.md`.
