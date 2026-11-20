# Keepwell Part B (Experience Layer) — Hand-Off Package (`docs/HANDOFF_B.md`)

**Branch:** `part-b/experience` | **Workspace:** Dart Pub Workspaces (`apps/pubspec.yaml`, web-only Flutter 3.50.0 / Dart 3.14.0)

---

## 1. Run It (Clean Machine)

### Prerequisites
- Flutter `3.50.0` (stable, web enabled), Dart `3.14.0`
- Python `3.11+` (with `fastapi`, `uvicorn`, `websockets`, `pytest`, `httpx` — already in `keepwell/.venv`)
- Node.js `20+` & Firebase CLI (`firebase-tools`) + OpenJDK 21 (for Firebase emulators)

### Commands & Expected Output
```bash
# 1. Start Part B mocks (REST :8081 + Live WebSocket :8082)
cd apps && make mocks
# Expected:
#   REST API : http://localhost:8081/v1  (OpenAPI: http://localhost:8081/openapi.json)
#   Live WS  : ws://localhost:8082/v1/live/call

# 2. Verify mocks suite
keepwell/.venv/bin/pytest mocks/test_mocks.py -v
# Expected: 7 passed

# 3. Resolve Dart pub workspace & analyze all 7 packages
cd apps && flutter pub get && flutter analyze kw_ui kw_ui/example kw_client console field household brand
# Expected: No issues found!

# 4. Run all Dart & Flutter tests
cd apps/kw_client && dart test          # Expected: 8 passed
cd ../kw_ui && flutter test             # Expected: 15 passed
cd ../console && flutter test           # Expected: 3 passed
cd ../field && flutter test             # Expected: 5 passed
cd ../household && flutter test         # Expected: 5 passed
cd ../brand && flutter test             # Expected: 4 passed

# 5. Build all 4 web apps for Firebase Hosting (or switch to Part A via --dart-define)
cd apps && make build-web API_BASE_URL=https://<kw-api-host>/v1 LIVE_WS_URL=wss://<kw-api-host>/v1/live/call FIREBASE_PROJECT_ID=<real-project> DEMO_MODE=false PAYMENT_MODE=sandbox
# Expected: Built build/web for console, field, household, brand

# 6. Optional: Run Firestore emulator + C03 Stage time-lapse
cd infra/frontend && firebase emulators:start --only auth,firestore
python3 mocks/firestore/seed_emulator.py
python3 mocks/firestore/timelapse_c03.py
```

---

## 2. What Is Complete (Contract §5–§8 & §6.3 Checklist)

- **Design System (`apps/kw_ui/` + `apps/kw_ui/example/`):**
  - 5 themes (`light`, `dark`, `highContrastLight`, `highContrastDark`, `projector`), M3 Expressive native `SpringSimulation` motion tokens (`kw_motion.dart`), shape/spacing/breakpoint tokens, `en-IN` lakh currency & IST formatters, `en`/`hi`/`te` runtime strings (`kw_strings.dart`).
  - All 16+ components (`KwUrgencyChip`, `KwCaseCard`, `KwStatusStepper`, `KwConsentGateCard`, `KwConfidenceMeter`, `KwSourceCitationChip`, `KwCandidateScoreBar`, `KwTranscriptBubble`, `KwWaveformControls`, `KwEventRow` covering all 34 Contract §8 event types + unknown fallback, `KwSlotPicker`, `KwRouteEtaBar`, `KwMoneyLine` with `"Needs checking"`, `KwOtpInput`, `KwFvrGauge`, `KwEmptyState`/`KwErrorState`/`KwSkeletonLoader`).
  - Verified by `apps/kw_ui/test/kw_ui_test.dart` (**15/15 passed**, including 200% text scale in `en`/`hi`/`te`).
- **Client Package (`apps/kw_client/`):**
  - All 38 Contract §5.1/§8 models (`models.dart`) with snake_case JSON mapping and unknown-field tolerance.
  - Full Contract §5.2 REST client (`kw_api_client.dart`) with Bearer auth, `Idempotency-Key`, `X-Keepwell-Key`, retries, and `KwApiException`.
  - Contract §7 WebSocket client (`live_call_client.dart`) with sealed `LiveServerMessage` union and `go_away` auto-reconnect.
  - 9-centre demo & Firebase Auth helper (`kw_auth.dart`) and Firestore REST / polling `LiveFeedRepository`.
  - Verified by `apps/kw_client/test/kw_client_test.dart` (**8/8 passed**).
- **Mocks (`mocks/`):**
  - `mocks/fixtures/build_fixtures.py` builds normalized JSON directly from `keepwell_sim_dataset_v0.2.zip` (9 centres, 37 technicians, 165 households, 341 appliances, 20 inbox cases, 14 safe fixes, all 5 payment states, debrief with unmatched part).
  - `mocks/rest/server.py` (all Contract §5 endpoints + stateful mutations + `X-Mock-Fail`), `mocks/ws/server.py` (C03 replay + echo mode), `mocks/firestore/{seed_emulator,timelapse_c03}.py`, `mocks/run_mocks.py`.
  - Verified by `mocks/test_mocks.py` (**7/7 passed**).
- **Centre Console (`apps/console/`):**
  - Sign-In, adaptive List-Detail Case Board (strict `safety -> urgent -> standard -> planned` + `needed_by`), Case Detail with Reclassify & Reassign + 10s Undo SnackBar, **Live Stage View (`/stage`)** with Projector Mode & built-in C03 live playback, Test-Call Sheet, Technicians & Calendar with keyboard-accessible Reschedule & static map fallback, Overview with FVR-14 gauge & table toggle, Operations tables (Stock, Prices, Safe-Fix overdue badges, Overrides + CSV export), Demo Control Drawer.
  - Verified by `apps/console/test/console_test.dart` (**3/3 passed**) + `flutter build web`.
- **Field Apps (`apps/field/`):**
  - Role-based Sign-In routing to Technician Shell (offline-first queued outbox + sync banner, privacy-gated address/phone, Already Tried list, firm quote composer with variance, spoken debrief review with `"Needs checking"` resolution, OTP closure) and Parts Centre Shell (≥52dp one-handed Accept/Ready/Handover + stock stepper).
  - Verified by `apps/field/test/field_test.dart` (**5/5 passed**) + `flutter build web`.
- **Household Surfaces (`apps/household/`):**
  - Zero-sign-in routes (`/`, `/whatsapp`, `/call`, `/v/:token`, `/home/:token`, `/quotes/:token`, `/otp/:token`), Material 3 WhatsApp Simulator (9 centres + household picker, no WhatsApp branding), Call Dialer with verbatim recording notice & live captions, Video-Link `/v/<token>` with 4 `ui_hint` framing guides + 1 fps counter + camera-denied still-photo fallback, Home Memory with explainable Care Index, Quote Approval + Google Pay TEST sheet / UPI Intent / Sandbox completion + explicit OTP-only closure boundary.
  - Verified by `apps/household/test/household_test.dart` (**5/5 passed**) + `flutter build web`.
- **Brand & Retailer Portal (`apps/brand/`):**
  - Sign-In, Forwarded Requests with C18 authority-decline visibility, Brand Forward & Retailer Handover forms (`202` response card), FVR-14 Analytics + accessible table + Looker Studio embed/fallback.
  - Verified by `apps/brand/test/brand_test.dart` (**4/4 passed**) + `flutter build web`.
- **Frontend Infrastructure & Skills (`infra/frontend/`, `.agents/part-b/`):**
  - `firebase.json` (4 Hosting targets + emulators), `.firebaserc`, `firestore.rules` (strict Contract §6), `firestore.indexes.json`, `app_check.md`, `@firebase/rules-unit-testing` suite (`test_rules/firestore_rules.test.mjs`), 8 skills + 5 workflows (<40 lines each).

---

## 3. What Is Not Done (Honest List)

1. **Live Browser Media Capture (`getUserMedia` / `AudioWorklet`):** Call Dialer and Video-Link pages implement the full Contract §7 WebSocket protocol and UI state machine with simulated audio/frame triggers in web/headless mode; wiring raw Chrome `AudioWorklet` PCM16 capture and `HTMLVideoElement` canvas JPEG encoding is a clean next step during Integrator rehearsal.
2. **Lighthouse JSON & Visual Screenshots (`docs/design/lighthouse/`):** Not yet captured against a live hosted server; automated semantics, ≥48dp target, and 200% text-scale assertions are verified in `flutter test`.
3. **Firebase Rules Emulator Execution:** `infra/frontend/test_rules/firestore_rules.test.mjs` passed `node --check` and JSON validation; requires running `npm install && firebase emulators:exec "npm test"` once in `infra/frontend/test_rules/`.
4. **Native-Speaker Copy Review:** Hindi (`hi`) and Telugu (`te`) UI chrome strings are complete drafts ready for native-speaker sign-off.

---

## 4. Decisions & Change Requests

Copied from `docs/DECISIONS_B.md`:
- **D-B01:** Auto-resolve `input/dataset/` first, falling back to `keepwell/docs_v1/keepwell_sim_dataset_v0.2.zip`.
- **D-B02:** Standardised lightweight `ChangeNotifier` / state controllers + `kw_client` DI across apps (kept dependencies minimal for instant Dart pub workspace resolution).
- **D-B03:** Hash/URL route parsing for `/stage`, `/v/:token`, `/home/:token`, `/quotes/:token`, `/otp/:token`.
- **D-B04:** Native Flutter `SpringSimulation` implementation of Material 3 Expressive springs inside `kw_ui`.
- **D-B05:** Python FastAPI + WebSocket mock servers (`mocks/rest`, `mocks/ws`) with `X-Mock-Fail` error injection.
- **D-B06:** `asia-south1` production defaults with local emulator/mock defaults in dev.
- **D-B07:** Dart pub workspaces (`apps/pubspec.yaml`, no Melos) and Flutter web-only configuration per user directive.
- **D-B08:** Material 3 chat styling for `"WhatsApp simulator"` with zero WhatsApp logos/trade dress.

No Contract Change Requests (`contract/CHANGE_REQUESTS.md`) were required — every endpoint, model, Firestore path, and WebSocket frame matched `SHARED_CONTRACT.md` v1 cleanly.

---

## 5. Google Products Used

| Google Product / API / Tool | Where Used | Evidence |
|---|---|---|
| **Flutter 3.50.0 & Dart 3.14.0 (Web)** | All 4 web apps + `kw_ui` + `kw_client` | `flutter analyze` (0 issues), 40/40 Dart/Flutter tests, 4/4 `flutter build web` builds |
| **Material 3 Expressive & Material Symbols** | `apps/kw_ui/` themes, springs, 16+ components | `apps/kw_ui/test/kw_ui_test.dart` (15/15 passed) |
| **Google Fonts (Roboto Flex, Noto Sans Devanagari/Telugu/Mono)** | `apps/*/web/index.html`, `kw_theme.dart` | Loaded across all 5 web entrypoints |
| **Gemini Live API Protocol (Client)** | `apps/kw_client/lib/src/live/live_call_client.dart`, `call_dialer_screen.dart`, `video_link_screen.dart`, `stage_view_screen.dart` | `mocks/ws/server.py` + `kw_client_test.dart` + `household_test.dart` |
| **Firebase Hosting, Auth, Firestore, App Check** | `infra/frontend/{firebase.json,firestore.rules,firestore.indexes.json,app_check.md}`, `kw_auth.dart`, `firestore_client.dart` | Validated JSON/JS configs + `kw_client_test.dart` |
| **Google Pay API for Web (TEST)** | `apps/household/lib/src/quote_approval_screen.dart` | Verified in `household_test.dart` |
| **Google Maps (Deep Link + Static Fallback)** | `apps/console/lib/src/calendar_screen.dart`, `apps/field/lib/src/technician/visit_detail_screen.dart` | `KwRouteEtaBar` + Maps URL launch |
| **Looker Studio (Embed + Native Fallback)** | `apps/brand/lib/src/analytics_screen.dart` | Verified both fallback & configured modes in `brand_test.dart` |

---

## 6. Risks for Merge, Deploy & Demo

1. **Firestore Timestamp Encoding:** `KwFirestoreClient` decodes standard Firestore REST `timestampValue` strings; verify Part A's projection writes ISO 8601 UTC timestamps matching Contract §6.
2. **CORS on `kw-api`:** All 4 Firebase Hosting origins (`console`, `field`, `household`, `brand`) must be allowlisted in Part A's FastAPI CORS middleware.
3. **Live API Preview Limits:** Keep C03 stage demo under 5 minutes; `LiveCallClient` handles `go_away` transparently, and Stage View falls back smoothly if the venue network drops WebSockets.

---

## 7. Quality Report

- **Static Analysis (`flutter analyze` across all 7 workspace packages):** `No issues found!`
- **Test Counts:** **47 / 47 passed** (`mocks`: 7, `kw_client`: 8, `kw_ui`: 15, `console`: 3, `field`: 5, `household`: 5, `brand`: 4).
- **Web Production Builds:** All 4 Firebase Hosting targets (`console`, `field`, `household`, `brand`) compiled cleanly via `flutter build web`.
- **Rubric Self-Assessment:** See [docs/rubric_B.md](file:///Users/Shared/Files%20From%20e.localized/PDM/Google%20buildathon%20/Google_Startup_Buildathon/docs/rubric_B.md).
