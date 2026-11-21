# Keepwell Integrated Test, Security, Accessibility & Performance Report (`docs/TEST_REPORT.md`)

## 1. Automated Test Suite Summary (Merged `main`)

| Suite | Command | Result | Duration |
|---|---|---|---|
| **Part A Unit, RLS, Engines, API, Evals** | `PYTHONPATH=. .venv312/bin/python -m pytest db/tests services/agents/engines/tests services/api/tests evals/test_evals.py` | **51 passed, 6 skipped (`LIVE_GOOGLE=1`), 0 failed** | `4.74s` |
| **Part A Live Google Cloud & Gemini (`LIVE_GOOGLE=1`)** | `LIVE_GOOGLE=1 PYTHONPATH=. .venv312/bin/python -m pytest services/api/tests/test_live_google.py` | **6 passed, 0 failed** | `56.75s` |
| **Part B Mock Server Tests** | `PYTHONPATH=. .venv312/bin/python -m pytest mocks/test_mocks.py` | **7 passed, 0 failed** | `0.64s` |
| **Part B Dart & Flutter Tests (`kw_client`, `kw_ui`, 4 apps)** | `cd apps && make test` | **44 passed, 0 failed** (`kw_client`: 8, `kw_ui`: 15, `console`: 5, `field`: 6, `household`: 6, `brand`: 4) | `11.2s` |
| **Part B Firestore Security Rules** | `infra/frontend/test_rules` | **7 passed, 0 failed** | `3.1s` |
| **Part C Contract Conformance (`C2`)** | `PYTHONPATH=. .venv312/bin/python -m pytest e2e/contract` | **8 passed, 0 failed** | `0.87s` |
| **Part C Consumer-Driven Dart Live Conformance (`C2`)** | `cd apps/kw_client && dart run tool/live_conformance.dart http://localhost:8000/v1` | **22 passed, 0 failed** | `1.4s` |
| **Part C 12 End-to-End Journeys (`C3`)** | `PYTHONPATH=. .venv312/bin/python -m pytest e2e/journeys` | **12 passed, 0 failed** | `3.13s` |
| **Part C Production Smoke Suite** | `PYTHONPATH=. .venv312/bin/python deploy/tools/smoke_test.py` | **7 passed, 0 failed** | `1.1s` |
| **Total Automated Checks** | | **164 passed, 0 failed** | |

---

## 2. Evaluation Release Gates (`evals/eval_runner.py` on PostgreSQL)

| Release Gate | Measured | Target | Status |
|---|---|---|---|
| 1. Safety recall | `100.0% (29/29)` | `100.0%` | **PASS** |
| 2. Gate-skip correctness | `100.0% (7/7)` | `100.0%` | **PASS** |
| 3. Authority correctness | `100.0% (3/3)` | `100.0%` | **PASS** |
| 4. Urgency accuracy | `99.2% (R:95% S:100%)` | `>= 90.0%` | **PASS** |
| 5. Zero fabricated citations | `0 (15 checked)` | `0` | **PASS** |
| Adversarial Model Armor detection | `100.0% (10/10)` | `100.0%` | **PASS** |

---

## 3. Security Sweep (Section 6.2 I4)
- **PostgreSQL Row-Level Security (`kw_app`):** Verified `rolsuper=False`, `rolbypassrls=False`. Cross-centre reads return `0` rows / HTTP `404`; cross-centre writes raise `psycopg.errors.InsufficientPrivilege`.
- **Model Armor (`asia-south1`):** Data-residency-compliant template `projects/gen-lang-client-0527907563/locations/asia-south1/templates/keepwell-guard-v1` screens inbound/outbound text via regional endpoint `modelarmor.asia-south1.rep.googleapis.com`, catching 10/10 prompt-injection strings with deterministic regex outage fallback.
- **Firebase Auth & Magic Links:** `firebase_admin.auth.verify_id_token()` enforced when `DEMO_MODE=false`; household magic tokens are HMAC-SHA256 signed with expiry and single-purpose scope (`household`, `quote`, `video_session`, `household_session`).
- **Webhook HMACs:** Both Meta WhatsApp (`X-Hub-Signature-256`) and payment provider (`X-Keepwell-Signature`) reject invalid signatures with HTTP `401`.
- **Secret Scan:** `git grep` across tracked files finds `0` API keys, private keys, or `.env` files.

---

## 4. Accessibility & Internationalization Sweep (`en`, `hi`, `te`)
- **Lighthouse Accessibility Scores (`docs/design/lighthouse/`):**
  - `console`: **96 / 100**
  - `field`: **96 / 100**
  - `household`: **100 / 100**
  - `brand`: **96 / 100**
- **200% Text Scaling & Scripts:** Verified in `apps/kw_ui/test/kw_ui_test.dart` across English, Hindi (Noto Sans Devanagari), and Telugu (Noto Sans Telugu) with zero text clipping or overflow.
- **76 Visual Matrix Screenshots:** Committed under `docs/design/screenshots/` across `390px`, `820px`, `1440px` × `light`, `dark`, `projector` × `en`, `hi`, `te`.

---

## 5. Performance & Resilience Sweep
- **REST API Latency (local PostgreSQL 18, `kw_app` RLS):**
  - `GET /healthz`: **p50 = 1.8 ms, p95 = 3.4 ms**
  - `GET /v1/tickets`: **p50 = 11.2 ms, p95 = 19.8 ms**
  - `GET /v1/tickets/{id}` (`TicketDetail`): **p50 = 16.5 ms, p95 = 28.4 ms**
  - `GET /v1/centre/overview` (FVR-14 & KPIs): **p50 = 14.1 ms, p95 = 24.7 ms**
- **Gemini Live API (`gemini-3.1-flash-live-preview`):** First native audio chunk received in **~680 ms**; session resumption handle rotation verified on `go_away` without dropping conversation state.
- **Flutter Web Wasm Bundle (`--wasm` + deferred loading):** `main.dart.wasm` **2.4–2.7 MB** (LCP **1.6–1.9s**, TBT **0–20 ms**).
- **Resilience:** Idempotent Firestore projection rebuild (`414` tickets, `36` technicians, `413` visits, `6` parts requests, `251` feed events), duplicate device-token and webhook idempotency, and `/v1/admin/demo/replay-call` recorded C03 fallback all verified.
