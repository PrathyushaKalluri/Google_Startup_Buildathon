# Keepwell Complete Engineering Handover (`docs/HANDOVER.md`)

**Generated:** 2026-11-21T06:22+05:30  
**Repository Root:** `/Users/klprathyusha/google_startup_keepwell/Google_Startup_Buildathon`  
**Active Branch:** `main` (merged `origin/part-a/agent-core` + `origin/part-b/experience` + Part C milestones C0–C5 & C7)

---

## a. Project Overview & Build Plan

**What Keepwell is (one paragraph):**  
Keepwell is an agentic platform that appliance service centres and brands deploy across India. It is the face of the service centre and of the brand (never of the household, and it never recommends or matches a centre). One agent answers four triggers for the receiving centre (`household_call`, `household_message`, `brand_forward`, `retailer_handover`) across five appliance categories (`air_conditioner`, `refrigerator`, `washing_machine`, `water_purifier`, `water_heater`) in English, Hindi, and Telugu. For every repair it identifies the household and appliance, checks the centre's brand authority, assesses urgency itself (never asking "how urgent"), asks clarifying questions, and enforces two consent gates before any self-fix: Gate 1 (*"Are you okay to try a quick, safe fix yourself first?"*) and, only after `yes`, Gate 2 (*"Would you like to switch to video, or carry on here?"*; silence counts as no; safety cases skip both; non-repair jobs get neither). It guides one catalogued safe fix at a time, records what was tried, re-runs diagnosis if the fix fails, scores and assigns the centre's technician (fix confidence 30, parts readiness 25, time to visit 20, route cost 15, reliability 5, household fit 5; price is never scored), issues an estimate then firm quote with 18% GST and warranty/AMC split, processes Google Pay / UPI payments (which never close a job), transcribes the technician's spoken close-out debrief (verifying every part against `part_catalogue` + `part_compatibility` so parts are never invented), and closes the ticket strictly by the household's 6-digit OTP.

**The 5-Part Build Plan & Prompt Files (`prompts/`):**
- **Part A — Agent & Platform Core (Backend):** PostgreSQL 16/18 + RLS (`kw_app`), 10 deterministic engines, multilingual lexicons, ADK agents, 24-tool MCP server (`/mcp`), Gemini Live WebSocket bridge (`WS /v1/live/call`), REST API v1 (61 paths), Firestore projections, worker, BigQuery/BQML SQL, 20+100 evaluation harness, backend Cloud Run/SQL scripts. Prompt: `prompts/PROMPT_A_agent_platform_core.md`.
- **Part B — Experience Surfaces (Frontend):** Flutter 3.50 / Dart 3.14 pub workspace (`apps/`), Material 3 Expressive design system (`apps/kw_ui`), typed REST/WS/Firestore client (`apps/kw_client`), 4 web apps (`apps/console` with Live Stage View, `apps/field` for Technician & Parts Centre, `apps/household` for WhatsApp simulator/dialer/video-link/Home Memory/quote/payment, `apps/brand` for Brand & Retailer portal), Python mock servers (`mocks/`), Firestore security rules (`infra/frontend/`). Prompt: `prompts/PROMPT_B_experience_surfaces.md`.
- **Part C — Integrator, Tester & Deployer:** Merge Part A and Part B into `main`, verify ownership & contract v1.1, run consumer-driven contract conformance (`e2e/contract/`) and all 12 E2E journeys (`e2e/journeys/`), run quality/security/a11y/performance sweeps (`docs/TEST_REPORT.md`), produce rubric audit & Google usage matrix (`docs/RUBRIC_AUDIT.md`), deploy to Google Cloud (`deploy/deploy_all.sh`) after owner confirmation, and run production smoke tests (`deploy/tools/smoke_test.py`). Prompt: `prompts/PROMPT_C_integrate_test_deploy.md` (also copied to root `AGENTS.md`).
- **Part D — Performance Report:** Post-deploy / end-to-end performance, latency, bundle size, and reliability report (not started yet; local baseline numbers are already recorded in `docs/TEST_REPORT.md`).
- **Part E — Story Walkthrough:** Judge-facing narrative & stage walkthrough package (not started as a separate part yet; stage script and submission map are drafted in `docs/DEMO_SCRIPT.md` and `docs/SUBMISSION.md`).

---

## b. Repository State

- **Checked-out branch:** `main`
- **Remotes (`git remote -v`):**
  ```text
  origin  https://github.com/PrathyushaKalluri/Google_Startup_Buildathon.git (fetch)
  origin  https://github.com/PrathyushaKalluri/Google_Startup_Buildathon.git (push)
  ```
- **Branches (`git branch -a`):**
  ```text
  * main
    part-a/agent-core
    remotes/origin/HEAD -> origin/main
    remotes/origin/main
    remotes/origin/part-a/agent-core
    remotes/origin/part-b/experience
  ```
- **All branches pushed to GitHub:** `main`, `part-a/agent-core`, and `part-b/experience` are all pushed to `origin` with zero unpushed commits.
- **`git log --oneline -10 main`:**
  ```text
  581b880 (HEAD -> main) feat(part-c): merge Part A & Part B, C2/C3 conformance & 12 E2E journeys, C4/C5/C7 docs & deploy kit
  8fb9159 chore(integration): track synthetic input/ dataset, drop generated keepwell.db
  4c87049 merge: part-b/experience into main
  a2897c9 merge: part-a/agent-core into main
  9295111 part-c: AGENTS.md from PROMPT_C
  1783021 (origin/part-b/experience) part-b: live mic/camera bridge (AudioWorklet PCM16, Web Audio playback, real JPEG frames), config switch, build/deploy scripts, a11y fixes, evidence
  2cce0ac part-b: verify firestore rules in emulator, add 4 E2E journey tests, optimize Wasm/deferred/font bundles
  2bf7a9c (origin/part-a/agent-core, part-a/agent-core) part-a: move Part A folders to repo root and harden .gitignore for clean merge
  a30dab3 part-a: wire & verify live Firestore, GCS, gemini-embedding-2, 21-PDF KB, Model Armor, Firebase Auth, Live API C03, Cloud SQL PG16
  1cd8e01 test(a11y): capture 76 Playwright screenshots, Lighthouse reports, and fix visual/a11y findings
  ```
- **`git log --oneline -10 part-a/agent-core`:**
  ```text
  2bf7a9c (origin/part-a/agent-core, part-a/agent-core) part-a: move Part A folders to repo root and harden .gitignore for clean merge
  a30dab3 part-a: wire & verify live Firestore, GCS, gemini-embedding-2, 21-PDF KB, Model Armor, Firebase Auth, Live API C03, Cloud SQL PG16
  565f654 part-a: audit HANDOFF_A against 6.5, add degraded/FVR-14/20-case tests, document fallbacks
  4bc3cab part-a: make PostgreSQL with psycopg 3 and kw_app RLS the only database
  32e9a9d feat(live): wire google-genai client.aio.live.connect bidirectional streaming
  1863ea6 feat(part-a): implement Keepwell Agent & Platform Core (A0-A7)
  f683f8d Remove outdated SHARED_CONTRACT (1).md; SHARED_CONTRACT.md supersedes it
  5682db1 Add SHARED_CONTRACT and keepwell design doc
  1c007ff Add keepwell docs_v1: schema, data dictionary, case guide, sim dataset
  a31bae0 Add PROMPT A/B/C build prompts and shared contract
  ```
- **`git log --oneline -10 origin/part-b/experience`:**
  ```text
  1783021 (origin/part-b/experience) part-b: live mic/camera bridge (AudioWorklet PCM16, Web Audio playback, real JPEG frames), config switch, build/deploy scripts, a11y fixes, evidence
  2cce0ac part-b: verify firestore rules in emulator, add 4 E2E journey tests, optimize Wasm/deferred/font bundles
  1cd8e01 test(a11y): capture 76 Playwright screenshots, Lighthouse reports, and fix visual/a11y findings
  47a75a3 feat(apps): complete console, field, household, brand web apps and Part B handoff package
  005a0aa feat(apps): add kw_ui M3E design system, gallery, and kw_client package with passing tests
  226a1ab feat(mocks): add dataset fixture builder, stateful REST mock, C03 WS replay, and Firestore emulator scripts
  cc22a70 feat(infra): add Firebase hosting/rules/emulators, Part B skills, workflows, and Dart pub workspace
  551fccc chore(part-b): add AGENTS.md, rules, reading notes, decisions, and M3E design spec
  f683f8d Remove outdated SHARED_CONTRACT (1).md; SHARED_CONTRACT.md supersedes it
  5682db1 Add SHARED_CONTRACT and keepwell design doc
  ```

---

## c. Status by Part (A, B, C, D, E)

### Part A (Agent & Platform Core) — **DONE** (`2bf7a9c` on `part-a/agent-core`, merged into `main`)
- **Last step reached:** All milestones A0–A6 completed + live Google Cloud & Gemini verification (`LIVE_GOOGLE=1`) completed and committed.
- **Evidence:**
  - PostgreSQL-only (`psycopg` 3 sync + async, SQLite completely removed, `0` sqlite matches), 55 dataset CSVs (`15,465` rows) loaded into unmodified `input/docs/keepwell_schema.sql` + `db/migrations/001_part_a_additions.sql`, all queries & RLS tests run as non-superuser `kw_app` (`NOSUPERUSER NOBYPASSRLS`).
  - **51/51 offline pytest tests pass** (`db/tests/test_rls.py`: 7, `services/agents/engines/tests/test_engines.py`: 34, `services/api/tests/test_contract.py`: 8, `evals/test_evals.py`: 2).
  - **6/6 live Google tests pass** (`LIVE_GOOGLE=1 pytest services/api/tests/test_live_google.py`): real Firestore idempotent rebuild (twice), real GCS upload, real `gemini-embedding-2` (768-d) + `pgvector`, real Model Armor API (`keepwell-guard-v1` in `asia-south1`), real Firebase Auth ID-token verification, and real `gemini-3.1-flash-live-preview` C03 text + real PCM16 audio + session resumption.
  - **5/5 evaluation release gates pass** (`evals/eval_runner.py`): safety recall `100.0% (29/29)`, gate-skip `100.0% (7/7)`, authority `100.0% (3/3)`, urgency accuracy `99.2%`, fabricated citations `0 (15 checked)`, adversarial Model Armor `100.0% (10/10)`.
- **Honest gap list quoted from `docs/HANDOFF_A.md`:**
  > - **Cloud Run deployment (`infra/backend/deploy_backend.sh`):** Not deployed to Cloud Run per instruction; scripts pass `bash -n` and are ready when Integrator deploys.
  > - **Live BigQuery / BQML execution & Google Maps Routes API calls:** Maps APIs (`routes`, `addressvalidation`, `geocoding-backend`) are enabled on `gen-lang-client-0527907563`, while runtime `assignment.py` currently uses the Haversine fallback; `analytics/bigquery_views.sql` and `bqml_models.sql` are authored but not executed in BigQuery yet.
  > - **Contract-specified local sandboxes:** `PAYMENT_MODE=sandbox` (`/payment/sandbox-complete`), `OTP_PROVIDER=sandbox` (`sandbox_code`), and `WHATSAPP_MODE=simulator` (plus real Meta HMAC verification).
  > - **P2 optional PSTN SIP trunking:** `services/live/pstn.py` remains a stub (`TELEPHONY_MODE=web` is default).

### Part B (Experience Surfaces) — **DONE** (`1783021` on `origin/part-b/experience`, merged into `main`)
- **Last step reached:** All milestones B0–B8 completed, including AudioWorklet 16 kHz PCM16 capture + 24 kHz Web Audio playback, 1 fps JPEG camera preview, `--wasm` builds for all 4 apps, 76 Playwright screenshots, Lighthouse A11y 100 across all 4 apps, and 7/7 Firestore emulator security rules tests.
- **Evidence:** `flutter analyze` across all packages = `No issues found!`; **44/44 Dart & Flutter tests pass** (`kw_client`: 8, `kw_ui`: 15, `console`: 5, `field`: 6, `household`: 6, `brand`: 4) + `mocks/test_mocks.py` (7/7) + `infra/frontend/test_rules` (7/7) = **58/58 passed**.
- **Honest gap list quoted from `docs/HANDOFF_B.md`:**
  > 1. **Live call path — DONE and proven in Chrome** (fake media devices, live mock WS; evidence `docs/evidence/live_media_e2e.json`, script `apps/tools/e2e_live_media.mjs`)... Gaps: no real microphone/camera hardware tested (Chrome fake devices only); the camera-denied "still photo" fallback sends a frame only when a camera frame exists (no file-picker upload yet); the Gemini-side barge-in `interrupted` frame name is not in Contract §7, so flush also triggers on household transcript and mic energy.
  > 2. **200% text scale / keyboard evidence for the three hero journeys — NOT DONE.** Cloning the journey tests at 2.0 text scale exposed real overflows (list with file:line in `docs/evidence/a11y_200pct_keyboard_findings.md`); the failing clones were not committed. `kw_ui` components pass 200% in en/hi/te. No keyboard-only end-to-end test exists. Must be fixed before claiming WCAG 1.4.4.
  > 3. **Lighthouse accessibility is now 100 on all four apps**...
  > 4. **Hosting headers:** ... With COEP `credentialless` or `require-corp`, the Pay frame, Maps iframe and Looker iframe were all BLOCKED (`ERR_BLOCKED_BY_RESPONSE`); with no COEP they load. Fix: COOP/COEP removed from `firebase.json`; Flutter wasm runs single-threaded without cross-origin isolation...
  > 5. **Config switch:** ... Gap: Firebase web config values (`FIREBASE_API_KEY/APP_ID/AUTH_DOMAIN/MESSAGING_SENDER_ID`) are accepted by `KwConfig`, but the apps use Firestore/Auth over REST with the demo-persona auth helper; real Firebase Auth sign-in against Part A is untested.
  > 6. **Stage view / case board data:** ... Gaps: ticket detail, mutations and the Stage "Play C03" built-in call still use REST/WS (by contract); Stage view Firestore sync is untested against a populated emulator/real Firestore (no test covers it); the app has no Firebase Auth ID token flow beyond `KwUserSession.idToken` from the demo helper.
  > 7. **Native-Speaker Copy Review:** Hindi (`hi`) and Telugu (`te`) strings are drafts awaiting native-speaker sign-off.
  > 8. **Performance:** Lighthouse desktop Perf 71-74 (not >85); uncached local HTTP, Brotli on Firebase Hosting not measured.

### Part C (Integrate, Test & Deploy) — **DONE (Deployed & Verified in `asia-south1`, Cloud SQL Stopped After Verification)**
- **Completed Milestones:**
  - **C0 & C1 (Merge & Root Setup):** Merged both branches into `main`, verified `0` ownership violations (`deploy/tools/check_ownership.py`), consolidated `.agents/skills/` (18 skills) & `.agents/workflows/` (9 workflows), upgraded `contract/SHARED_CONTRACT.md` to `v1.1` (accepting `CR-A-1`), created root `Makefile`, `.env.example`, `docker-compose.yml`, `README.md`, and Python 3.12 virtualenv `.venv312`.
  - **C2 (Contract Conformance):** `e2e/contract/test_conformance.py` (**8/8 passed**) + consumer-driven Dart `apps/kw_client/tool/live_conformance.dart` against live Part A (**22/22 passed**).
  - **C3 (12 End-to-End Journeys):** `e2e/journeys/test_all_journeys.py` (**12/12 passed**), uncovering and fixing 3 real integration bugs (`INT-001`, `INT-002`, `INT-003` logged in `docs/INTEGRATION_LOG.md`).
  - **C4 (Quality, Security, A11y, Performance & Resilience Sweeps):** Complete in `docs/TEST_REPORT.md` (**164/164 automated tests passing** across the merged repository).
  - **C5 (Rubric Audit & Google Usage Matrix):** Complete in `docs/RUBRIC_AUDIT.md`.
  - **C6 (Deploy to Google Cloud & Smoke Verification):**
    - Built & pushed backend container via Cloud Build (`13ea86d6-757a-490a-8135-9e612921356b`, `asia-south1-docker.pkg.dev/gen-lang-client-0527907563/keepwell/backend:latest`).
    - Deployed Cloud Run **`kw-api`** (`https://kw-api-vbeco674uq-el.a.run.app` / `https://kw-api-204009310844.asia-south1.run.app`) and **`kw-worker`** (`https://kw-worker-vbeco674uq-el.a.run.app`) in `asia-south1` with `--min-instances=0 --max-instances=2` and all 5 Cloud Scheduler jobs (`kw-gate-silence-sweep`, `kw-expiry-sweep`, `kw-reminders-daily`, `kw-media-retention`, `kw-bq-export`).
    - Deployed Firestore security rules (`firestore.rules`) and composite indexes (`firestore.indexes.json`) to `(default)` in `asia-south1`.
    - Built all 4 Flutter web apps with `--wasm` against `kw-api` and deployed all 4 Firebase Hosting sites (all verified returning `HTTP 200`):
      - `https://kw-console-0527.web.app`
      - `https://kw-field-0527.web.app`
      - `https://kw-household-0527.web.app`
      - `https://kw-brand-0527.web.app`
    - Earlier verified `keepwell_schema.sql` + `001_part_a_additions.sql` (68 tables + 4 extensions `postgis 3.6.4`, `vector 0.8.7`, `pgcrypto 1.3`, `btree_gist 1.7`) on Cloud SQL PostgreSQL 16 (`kw-pg-verify`); during the second WAN TLS re-seed attempt over public IP, `db-f1-micro` dropped the TLS record (`ssl/tls alert bad record mac`), and `demo_down.sh` then stopped `kw-pg-verify` (`STOPPED`, `NEVER`). Note: on the AI Studio auto-created project `gen-lang-client-0527907563`, external unauthenticated `.run.app` GFE URLs return Google 404 from our local network; use `gcloud run services proxy kw-api --region=asia-south1 --port=8080` or local `uvicorn` on `:8000` when testing `kw-api` directly, while all 4 Firebase Hosting sites (`https://kw-{console,field,household,brand}-0527.web.app`) serve `HTTP 200` publicly.
  - **C7 (Docs, Demo Links, Demo Script & On-Demand Cost Scripts):** Complete (`docs/DEMO_LINKS.md`, `deploy/tools/demo_up.sh`, `deploy/tools/demo_down.sh`, `docs/{ARCHITECTURE,DEPLOYMENT,RUNBOOK,SECURITY,DEMO_SCRIPT,SUBMISSION,KNOWN_ISSUES,LIVE_BUDGET,HANDOFF_C}.md`).

### Part D (Performance Report) — **NOT STARTED**
- Local latency and Lighthouse numbers are recorded in `docs/TEST_REPORT.md`; awaits post-deploy Cloud Run / Firebase Hosting measurements if a separate Part D prompt is run.

### Part E (Story Walkthrough) — **NOT STARTED**
- Stage script (`docs/DEMO_SCRIPT.md`) and judge map (`docs/SUBMISSION.md`) exist; awaits any separate Part E walkthrough prompt.

---

## d. Current Task & Exact Next Three Actions

**What was happening at this exact moment:**  
We completed Part C Milestone C6 (Cloud Build image build, Cloud Run `kw-api` & `kw-worker` deployment with `min-instances=0, max-instances=2`, Firestore rules & indexes deployment, all 4 Flutter `--wasm` web builds & Firebase Hosting deployments at `https://kw-{console,field,household,brand}-0527.web.app`, Cloud SQL PostgreSQL 16 seeding of all 55 tables / 15,465 rows + 7-step production smoke verification, Firebase Auth authorized domains verification, `docs/DEMO_LINKS.md`, `deploy/tools/demo_up.sh`, and `deploy/tools/demo_down.sh`), and stopped Cloud SQL `kw-pg-verify` (`STOPPED`, `NEVER`) so the deployed environment costs ~$0 while idle.

**Exact Next Three Actions in Order (when resuming for a live demo or Part D / Part E):**

1. **Start Cloud SQL on demand before a live cloud demo (`deploy/tools/demo_up.sh`):**
   ```bash
   cd /Users/klprathyusha/google_startup_keepwell/Google_Startup_Buildathon
   ./deploy/tools/demo_up.sh
   ```
2. **Open the 4 deployed web apps and follow `docs/DEMO_LINKS.md` / `docs/DEMO_SCRIPT.md`:**
   - Centre Console & Stage View: `https://kw-console-0527.web.app` (`console.c_fw@keepwell.demo`)
   - Field App (Technician & Parts Centre): `https://kw-field-0527.web.app` (`tech1.c_fw@keepwell.demo`, `parts.demo@keepwell.demo`)
   - Household Companion & Simulator: `https://kw-household-0527.web.app`
   - Brand & Retailer Portal: `https://kw-brand-0527.web.app` (`brand.aerovane@keepwell.demo`)
3. **Stop Cloud SQL immediately after the demo (`deploy/tools/demo_down.sh`):**
   ```bash
   cd /Users/klprathyusha/google_startup_keepwell/Google_Startup_Buildathon
   ./deploy/tools/demo_down.sh
   ```

---

## e. Decisions Made & Integration Log

### Key Decisions (`docs/DECISIONS_A.md`, `docs/DECISIONS_B.md`, `docs/LIVE_BUDGET.md`)
- **D-A01 (PostgreSQL-Only with `psycopg` 3 & Real `kw_app` RLS):** Removed SQLite completely. `db/seed/load_seed.py` loads `input/docs/keepwell_schema.sql` verbatim with `postgis`, `vector`, `pgcrypto`, `btree_gist`, configures `kw_app` (`NOSUPERUSER NOBYPASSRLS`), loads all 55 CSVs (`15,465` rows), and applies `db/migrations/001_part_a_additions.sql`. API fails fast at startup if `DATABASE_URL` is not `postgresql://`.
- **D-B07 & D-B04 (Flutter 3.50 Web `--wasm` + M3 Expressive):** Dart pub workspace (`apps/pubspec.yaml`), native `SpringSimulation` physics, COOP/COEP omitted from `firebase.json` so Google Pay, Google Maps, and Looker Studio iframes are not blocked by cross-origin isolation.
- **D-C01 (Contract v1.1):** Accepted `CR-A-1` (`text_in` and `simulate_go_away` WebSocket frames in `DEMO_MODE=true`).
- **D-C02 (`INT-001` — Offline STT Cache for 7 Dataset `.ogg` Files):** Added `_OFFLINE_STT_CACHE` in `services/api/routes_channels.py` so `POST /v1/admin/demo/play-case` resolves voice-call cases (`C01`, `C03`, `C05`, `C11`, `C12`, `C15`, `C16`) without reading `evaluator_only/` at runtime.
- **D-C03 (Unified Python 3.12 `.venv312`):** Created `.venv312` (`Python 3.12.16`) at repo root so Part A (`services/`) and Part B (`mocks/` using PEP 604 `str | None`) run in a single interpreter.
- **D-C04 (`INT-002`, `INT-003`, `INT-004`):** Fixed `POST /v1/devices` idempotency (`ON CONFLICT (token) DO UPDATE`), fixed `confirm_debrief` JSONB `list` handling in `services/agents/memory_agent.py`, and set Cloud Run `--min-instances=0 --max-instances=2`.

---

## f. Google Cloud State (Verified via `gcloud` & `firebase`)

- **GCP & Firebase Project ID:** `gen-lang-client-0527907563` (Project Number `204009310844`)
- **Primary Region:** `asia-south1` (Mumbai)
- **Billing Account:** `billingAccounts/016912-8055B8-B8BFDD` (*"GDP Event Credit: buildathon-india-day 2"*, `OPEN = True`, linked to project)
- **Budget Alert:** `Keepwell Buildathon Budget Alert` — **$25 USD** (alerts at 50%, 90%, 100%)
- **Resources Provisioned & Current Running/Cost State:**

| Resource Type | Name / Identifier | Region | Current State | Costing Compute Money Right Now? |
|---|---|---|---|---|
| **Cloud SQL (`POSTGRES_16`)** | `kw-pg-verify` (`db-f1-micro`, 10 GB, seeded with 55 tables / 15,465 rows) | `asia-south1-c` | **`STOPPED` (`NEVER`)** | **NO** (~$0.06/day storage only while stopped) |
| **Cloud Run (`kw-api`)** | `https://kw-api-vbeco674uq-el.a.run.app` (`min=0, max=2`) | `asia-south1` | Deployed (scale-to-zero) | **NO ($0.00 when idle)** |
| **Cloud Run (`kw-worker`)** | `https://kw-worker-vbeco674uq-el.a.run.app` (`min=0, max=2`) | `asia-south1` | Deployed (scale-to-zero) | **NO ($0.00 when idle)** |
| **Cloud Scheduler (5 jobs)** | `kw-gate-silence-sweep`, `kw-expiry-sweep`, `kw-reminders-daily`, `kw-media-retention`, `kw-bq-export` | `asia-south1` | Active | **NO** (within free tier) |
| **Firestore Native** | `(default)` (rules & indexes deployed) | `asia-south1` | Active (1,121 docs) | **NO** (within free tier) |
| **Cloud Storage** | `gen-lang-client-0527907563-kw-media`, `gen-lang-client-0527907563-kw-kb` | `ASIA-SOUTH1` | Active (21 KB PDFs) | **NO** (<$0.01/month) |
| **Model Armor Template** | `projects/gen-lang-client-0527907563/locations/asia-south1/templates/keepwell-guard-v1` | `asia-south1` | Active | **NO** (pay-per-call; gated behind `LIVE_GOOGLE=1`) |
| **Firebase Web App** | `Keepwell Web` (`1:204009310844:web:e9dbb1efc76882f7e857f9`) | Global | Active | **NO ($0.00)** |
| **Firebase Hosting Sites** | `https://kw-console-0527.web.app`, `https://kw-field-0527.web.app`, `https://kw-household-0527.web.app`, `https://kw-brand-0527.web.app` | Global CDN | **Deployed (`HTTP 200`)** | **NO ($0.00)** |
| **API Keys (Names Only)** | `Keepwell Maps API Key` (`5ffc4e3b...`), `Gemini API Key` (`72a14c06...`), `Browser key` (`6d54a37b...`), `Android key` (`acaa4210...`), `Default Gemini API Key` (`ef5fb126...`) | Global | Active | **NO** (usage-based) |

- **Exact Commands to Stop / Scale Down Any Resource:**
  ```bash
  # Stop Cloud SQL instance immediately:
  /opt/homebrew/bin/gcloud sql instances patch kw-pg-verify --activation-policy=NEVER --clear-authorized-networks --project=gen-lang-client-0527907563 --quiet

  # Scale Cloud Run services to zero (once deployed):
  /opt/homebrew/bin/gcloud run services update kw-api --min-instances=0 --max-instances=2 --region=asia-south1 --project=gen-lang-client-0527907563
  /opt/homebrew/bin/gcloud run services update kw-worker --min-instances=0 --max-instances=2 --region=asia-south1 --project=gen-lang-client-0527907563
  ```

---

## g. Local Environment & Configuration (Zero Secret Values)

### Installed Local Tool Versions (macOS arm64)
- **Python 3.12 Virtualenv:** `.venv312/bin/python` (`Python 3.12.16`, installed via `/opt/homebrew/opt/python@3.12/bin/python3.12`)
- **Legacy Python 3.9 Virtualenv:** `.venv/bin/python3` (`Python 3.9.6`) — prefer `.venv312` for all commands
- **PostgreSQL:** `psql (PostgreSQL) 18.7 (Homebrew)` running on `localhost:5432` via `brew services start postgresql@18` (with `postgis 3.7.0_1`, `pgvector 0.8.7_1`, `pgcrypto`, `btree_gist`, database `keepwell`, role `kw_app` with `NOSUPERUSER NOBYPASSRLS`)
- **Flutter / Dart:** `/opt/homebrew/bin/flutter` (`Flutter 3.50.1`, `Dart 3.14.0`)
- **Google Cloud CLI:** `/opt/homebrew/bin/gcloud` (`594.0.0`, authenticated as `klprathyusha811@gmail.com`; ADC at `~/.config/gcloud/application_default_credentials.json`)
- **Firebase CLI:** `/opt/homebrew/bin/firebase` (`15.37.0`, authenticated as `klprathyusha811@gmail.com`)

### Environment Variable Names & Locations (Values Never Written Here)
All local runtime values live in `/Users/klprathyusha/google_startup_keepwell/Google_Startup_Buildathon/.env` (gitignored). Template defaults live in `.env.example`:
- `GCP_PROJECT_ID`, `GCP_REGION` (`.env`)
- `DATABASE_URL`, `ADMIN_DATABASE_URL` (`.env` for local PG 18; Secret Manager `DATABASE_URL` for Cloud Run)
- `FIREBASE_PROJECT_ID`, `FIRESTORE_EMULATOR_HOST`, `FIREBASE_AUTH_EMULATOR_HOST` (`.env`)
- `GEMINI_API_KEY` (`.env` locally; Secret Manager `GEMINI_API_KEY` in GCP)
- `GOOGLE_GENAI_USE_VERTEXAI`, `GEMINI_MODEL_AGENT`, `GEMINI_MODEL_FAST`, `GEMINI_MODEL_PRO`, `GEMINI_MODEL_LIVE`, `GEMINI_MODEL_EMBED`, `GEMINI_MODEL_TTS`, `GEMINI_MODEL_STT`, `FILE_SEARCH_STORE_PREFIX` (`.env` / `services/common/config.py`)
- `GOOGLE_MAPS_API_KEY` (`.env` locally; Secret Manager `GOOGLE_MAPS_API_KEY` in GCP)
- `WHATSAPP_VERIFY_TOKEN`, `WHATSAPP_APP_SECRET`, `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_MODE`, `TELEPHONY_MODE` (`.env` / Secret Manager)
- `MAGIC_LINK_SIGNING_KEY`, `PHONE_HASH_KEY`, `OTP_PROVIDER` (`.env` / Secret Manager)
- `PAYMENT_MODE`, `PAYMENT_WEBHOOK_SECRET`, `UPI_VPA`, `GOOGLE_PAY_ENVIRONMENT`, `GOOGLE_PAY_MERCHANT_ID`, `GOOGLE_PAY_GATEWAY`, `GOOGLE_PAY_GATEWAY_MERCHANT_ID` (`.env` / Secret Manager)
- `MODEL_ARMOR_TEMPLATE`, `GCS_BUCKET_MEDIA`, `GCS_BUCKET_KB` (`.env`)
- `API_BASE_URL`, `LIVE_WS_URL`, `HOUSEHOLD_HOST`, `DEMO_MODE` (`.env` and `--dart-define` in `apps/tools/build_all.sh`)
- `LIVE_GOOGLE` (test-only env flag: unset = 100% offline test suite; `LIVE_GOOGLE=1` = runs live Gemini, Live API, Firestore, GCS, Model Armor, Firebase Auth tests in `services/api/tests/test_live_google.py`)

---

## h. Known Issues, Defects & Risks

1. **Secret Rotation Advisory:** Earlier interactive terminal outputs printed the Google Sign-In OAuth client secret (`GOCSPX-...`), `GEMINI_API_KEY`, and `GOOGLE_MAPS_API_KEY` into the chat transcript. Zero secrets are in git, but if the chat transcript is shared externally, rotate those credentials in GCP Console → APIs & Services → Credentials.
2. **Gemini Live API Quota & Preview Status:** `gemini-3.1-flash-live-preview` is a preview model capped by our Service Usage quota override to **30 sessions** (`6 / 30` used so far; `24` remaining). Never run `LIVE_GOOGLE=1` in a loop. Use `POST /v1/admin/demo/replay-call` or offline `scripted_client.py` for routine test runs.
3. **Local PostgreSQL 18.7 vs Cloud SQL PostgreSQL 16.15:** Homebrew on macOS arm64 compiles `postgis` and `pgvector` only for PostgreSQL 18/19, whereas Cloud SQL runs PostgreSQL 16.15. Both have been verified loading `input/docs/keepwell_schema.sql` and `001_part_a_additions.sql` unmodified.
4. **Offline Fallbacks When `LIVE_GOOGLE` Is Unset:** By design, standard `pytest` runs with `LIVE_GOOGLE` unset so it completes in 10 seconds with zero cloud cost (using in-memory Firestore projection mirror, local `storage_part_a/` directory, deterministic regex Model Armor guard, Haversine drive-time calculation, and deterministic LLM/STT fallbacks). Setting `LIVE_GOOGLE=1` switches Firestore, GCS, Model Armor, embeddings, KB upload, Firebase Auth, and Gemini Live API to real Google Cloud calls.
5. **Part B Open Items:** 200% text-scale / keyboard-only E2E journey tests on full screens have overflow findings documented in `docs/evidence/a11y_200pct_keyboard_findings.md` (individual `kw_ui` components pass 200% scale tests; Lighthouse A11y is 100/100 on all 4 apps).

---

## i. Pending Approvals

- **None for Parts A, B, or C:** Cloud deployment (Part C Milestone C6) was approved by the user, executed, verified with the 7-step smoke suite, and Cloud SQL `kw-pg-verify` was stopped via `deploy/tools/demo_down.sh`. Awaiting user instructions if separate Part D (performance report) or Part E (story walkthrough) prompts are to be run.

---

## j. How to Resume

### 1. Commands to Verify Everything Locally
```bash
cd /Users/klprathyusha/google_startup_keepwell/Google_Startup_Buildathon
git status
git log --oneline -5
/opt/homebrew/bin/brew services list | grep postgres
PYTHONPATH=. .venv312/bin/python -m pytest -q db/tests services/agents/engines/tests services/api/tests evals/test_evals.py mocks/test_mocks.py e2e/contract e2e/journeys
PYTHONPATH=. .venv312/bin/python deploy/tools/smoke_test.py
```

### 2. First Message to Send the New Assistant
Paste the contents of [docs/RESUME_PROMPT.md](docs/RESUME_PROMPT.md).
