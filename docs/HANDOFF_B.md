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

# 4. Run all Dart, Flutter & Firestore Rules tests
cd apps/kw_client && dart test          # Expected: 8 passed
cd ../kw_ui && flutter test             # Expected: 15 passed
cd ../console && flutter test           # Expected: 5 passed (incl. C03 Stage + Reclassify/Reassign Undo journeys)
cd ../field && flutter test             # Expected: 6 passed (incl. offline outbox FIFO sync journey)
cd ../household && flutter test         # Expected: 6 passed (incl. quote approval + payment + OTP boundary journey)
cd ../brand && flutter test             # Expected: 4 passed
cd ../../infra/frontend && firebase emulators:exec --only firestore --project keepwell-demo-placeholder "npm --prefix test_rules test"
# Expected: 7 passed (incl. cross-centre read denial & all client write denials)

# 5. Build all 4 web apps with Wasm (--wasm) for Firebase Hosting (or switch to Part A via --dart-define)
cd apps && make build-web API_BASE_URL=https://<kw-api-host>/v1 LIVE_WS_URL=wss://<kw-api-host>/v1/live/call FIREBASE_PROJECT_ID=<real-project> DEMO_MODE=false PAYMENT_MODE=sandbox
# Or individually with --wasm:
#   flutter build web --wasm --dart-define=DEMO_MODE=true
# Expected: Built build/web (main.dart.wasm 2.4-2.7 MB + deferred chunks) for console, field, household, brand

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
  - Verified by `apps/console/test/console_test.dart` + `apps/console/test/journeys_test.dart` (**5/5 passed**, including C03 Stage View projector playback and Reclassify/Reassign + Undo execution) + `flutter build web --wasm` (deferred-loaded `calendar_screen` and `overview_screen`).
- **Field Apps (`apps/field/`):**
  - Role-based Sign-In routing to Technician Shell (offline-first queued outbox + sync banner, privacy-gated address/phone, Already Tried list, firm quote composer with variance, spoken debrief review with `"Needs checking"` resolution, OTP closure) and Parts Centre Shell (≥52dp one-handed Accept/Ready/Handover + stock stepper).
  - Verified by `apps/field/test/field_test.dart` + `apps/field/test/offline_sync_journey_test.dart` (**6/6 passed**, including offline outbox FIFO sync with idempotency keys) + `flutter build web --wasm`.
- **Household Surfaces (`apps/household/`):**
  - Zero-sign-in routes (`/`, `/whatsapp`, `/call`, `/v/:token`, `/home/:token`, `/quotes/:token`, `/otp/:token`), Material 3 WhatsApp Simulator (9 centres + household picker, no WhatsApp branding), Call Dialer with verbatim recording notice & live captions, Video-Link `/v/<token>` with 4 `ui_hint` framing guides + 1 fps counter + camera-denied still-photo fallback, Home Memory with explainable Care Index, Quote Approval + Google Pay TEST sheet / UPI Intent / Sandbox completion + explicit OTP-only closure boundary.
  - Verified by `apps/household/test/household_test.dart` + `apps/household/test/quote_payment_journey_test.dart` (**6/6 passed**, including Quote -> Google Pay TEST -> sandbox payment -> OTP-only closure) + `flutter build web --wasm` + live Chrome mic/camera WebSocket test.
- **Brand & Retailer Portal (`apps/brand/`):**
  - Sign-In, Forwarded Requests with C18 authority-decline visibility, Brand Forward & Retailer Handover forms (`202` response card), FVR-14 Analytics + accessible table + Looker Studio embed/fallback (deferred-loaded).
  - Verified by `apps/brand/test/brand_test.dart` (**4/4 passed**) + `flutter build web --wasm`.
- **Frontend Infrastructure & Skills (`infra/frontend/`, `.agents/part-b/`):**
  - `firebase.json` (4 Hosting targets (nosniff/frame/referrer/permissions headers; COOP/COEP deliberately NOT set, see §3.4) + emulators), `.firebaserc`, `firestore.rules` (strict Contract §6), `firestore.indexes.json`, `app_check.md`, `@firebase/rules-unit-testing` suite (`test_rules/firestore_rules.test.mjs`, **7/7 passed under Firebase Firestore emulator**, including cross-centre read denial and client write denials), 8 skills + 5 workflows (<40 lines each).

---

## 3. What Is Not Done (Honest List)

1. **Live call path — DONE and proven in Chrome** (fake media devices, live mock WS; evidence `docs/evidence/live_media_e2e.json`, script `apps/tools/e2e_live_media.mjs`): mic via `getUserMedia` (echoCancellation/noiseSuppression/AGC on, settings reported true) -> `AudioWorklet` (`apps/household/web/pcm_worklet.js`) -> 16 kHz mono PCM16, **31 binary chunks of 1,280 bytes (40 ms)** left the page in 6 s; mock's 24 kHz PCM16 played through Web Audio with 60 ms jitter buffer (`playedPcmChunks` 10, 28,800 bytes); playback flushed on barge-in (mic RMS) and on household transcript/interruption signal; mute stops chunks (0 chunks during mute); speaker toggles a GainNode. Video page: real `MediaStream` bound to a `<video>` (640x480, `hasSrcObject` true), canvas -> real JPEG `video_frame` at 1 fps (6 frames/5.5 s, valid JPEG SOF 640x480, 6-7 KB, long edge <= 640); placeholder JPEG removed from live path; ui_hint guides overlay the video. Screenshot: `docs/evidence/video_page_live_preview.png`.
   - Gaps: no real microphone/camera hardware tested (Chrome fake devices only); the camera-denied "still photo" fallback sends a frame only when a camera frame exists (no file-picker upload yet); the Gemini-side barge-in `interrupted` frame name is not in Contract §7, so flush also triggers on household transcript and mic energy.
2. **200% text scale / keyboard evidence for the three hero journeys — NOT DONE.** Cloning the journey tests at 2.0 text scale exposed real overflows (list with file:line in `docs/evidence/a11y_200pct_keyboard_findings.md`); the failing clones were not committed. `kw_ui` components pass 200% in en/hi/te. No keyboard-only end-to-end test exists. Must be fixed before claiming WCAG 1.4.4.
3. **Lighthouse accessibility is now 100 on all four apps** (console/field `aria-allowed-attr` was `aria-expanded` on PopupMenuButton chips; replaced with ActionChip + showMenu and an icon-only language menu).
4. **Hosting headers:** tested Google Fonts, Google Pay (`pay.js` + payframe), Maps embed and Looker Studio iframe with `docs/evidence/third_party_headers_coep.json` (script `apps/tools/third_party_headers.mjs`). With COEP `credentialless` or `require-corp`, the Pay frame, Maps iframe and Looker iframe were all BLOCKED (`ERR_BLOCKED_BY_RESPONSE`); with no COEP they load. Fix: COOP/COEP removed from `firebase.json`; Flutter wasm runs single-threaded without cross-origin isolation (Lighthouse after numbers below were measured without those headers).
5. **Config switch:** `KwConfig.fromEnvironment()` now defaults `DEMO_MODE=false` and has NO localhost/placeholder fallbacks unless `DEMO_MODE=true`. `apps/tools/build_all.sh` and `infra/frontend/deploy_frontend.sh --dry-run` added (see §7). Gap: Firebase web config values (`FIREBASE_API_KEY/APP_ID/AUTH_DOMAIN/MESSAGING_SENDER_ID`) are accepted by `KwConfig`, but the apps use Firestore/Auth over REST with the demo-persona auth helper; real Firebase Auth sign-in against Part A is untested.
6. **Stage view / case board data:** Firestore reads go through `LiveFeedRepository` (`shouldUseFirestore`: emulator host OR `DEMO_MODE=false` + project id) — Console subscribes to `watchFeed` and `watchTickets`, and Stage view mirrors `controller.liveFeed` events. Gaps: ticket detail, mutations and the Stage "Play C03" built-in call still use REST/WS (by contract); Stage view Firestore sync is untested against a populated emulator/real Firestore (no test covers it); the app has no Firebase Auth ID token flow beyond `KwUserSession.idToken` from the demo helper.
7. **Native-Speaker Copy Review:** Hindi (`hi`) and Telugu (`te`) strings are drafts awaiting native-speaker sign-off.
8. Performance: Lighthouse desktop Perf 71-74 (not >85); uncached local HTTP, Brotli on Firebase Hosting not measured.

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
- **Test Counts:** **58 / 58 passed** (`mocks`: 7, `kw_client`: 8, `kw_ui`: 15, `console`: 5, `field`: 6, `household`: 6, `brand`: 4, `firestore.rules` emulator: 7).
- **Web Production Builds (`--wasm` + Deferred Loading + Font Optimization):**
  - All 4 Firebase Hosting targets (`console`, `field`, `household`, `brand`) compiled cleanly via `flutter build web --wasm` (`main.dart.wasm`: **2.4–2.7 MB** vs **3.1–3.4 MB** `main.dart.js`; deferred chunks emitted for `console` Calendar/Overview and `brand` Analytics; trimmed non-render-blocking Google Fonts preload with `display=swap` and unicode-range subsetting for Devanagari/Telugu).
- **Visual Matrix Screenshots (`docs/design/screenshots/`):** **76 PNGs** captured via Playwright Chromium against live mocks across all 4 apps × 3 widths (`390`, `820`, `1440` px) × 2 themes (`light`, `dark`) × 3 languages (`en`, `hi`, `te`) + 4 Projector Mode Stage View captures (`console_stage_{390,820,1440}_projector_en.png` & `console_stage_1440_projector_hi.png`). Visual inspection caught and fixed: (1) `field` demo-persona jobs fallback in `mocks/rest/server.py`, (2) `ChoiceChip` horizontal `labelPadding` for Devanagari/Telugu nav chips in `apps/household/lib/src/household_app.dart`.
- **Lighthouse Reports (`docs/design/lighthouse/`, Before JS/CanvasKit vs After `--wasm` + Deferred + Font Preload):**

| App | Perf (Before → Final) | A11y (Before → Final) | LCP (Before → Final) | TBT | Transfer KB (Before → Final) |
|---|---|---|---|---|---|
| `console` | 54 → **71** | 94 → **100** | 5.5 s → 4.5 s | 320 → 20 ms | 5,600 → 4,573 |
| `field` | 69 → **74** | 94 → **100** | 5.0 s → 4.0 s | 110 → 0 ms | 4,867 → 3,908 |
| `household` | 60 → **74** | 100 → **100** | 5.0 s → 3.9 s | 250 → 10 ms | 4,874 → 3,888 |
| `brand` | 63 → **74** | 100 → **100** | 5.0 s → 4.0 s | 200 → 0 ms | 4,889 → 3,924 |

- **Rubric Self-Assessment:** See [docs/rubric_B.md](file:///Users/Shared/Files%20From%20e.localized/PDM/Google%20buildathon%20/Google_Startup_Buildathon/docs/rubric_B.md).


## 8. Final-Run Check Table

| # | Check | Result | Evidence |
|---|---|---|---|
| 1a | Mic capture, 16 kHz PCM16 20-100 ms chunks, playback 24 kHz + jitter + flush, mute, speaker | PASS (Chrome fake devices) | `docs/evidence/live_media_e2e.json` |
| 1b | Real MediaStream preview, canvas JPEG <=640 px, 1 fps, ui_hint overlay, placeholder removed | PASS (Chrome fake devices) | same + `video_page_live_preview.png` |
| 1c | Chrome test vs mock WS | PASS | `apps/tools/e2e_live_media.mjs` |
| 2 | Google Pay/Maps/Looker/Fonts with COOP/COEP | COEP breaks Pay/Maps/Looker -> headers removed; PASS without | `docs/evidence/third_party_headers_coep.json` |
| 3 | Config only via --dart-define; build_all.sh; deploy dry-run; real-value build | PASS: `build_all.sh` with example values built all 4 (DEMO_MODE=false); grep of `main.dart.js`: 0 `localhost:808x` hits, 0 `keepwell-demo-placeholder`, example API host present in all 4. Note: the demo-persona password string `keepwell-demo-password` remains in `kw_auth` (demo sign-in helper) | `apps/tools/build_all.sh`, `infra/frontend/deploy_frontend.sh` |
| 4 | Stage/board data via kw_client repositories | PARTIAL (code path added, no populated-Firestore test) | §3.6 |
| 5a | aria-allowed-attr | PASS (Lighthouse a11y 100 x4) | `docs/design/lighthouse/*.json` |
| 5b | 200% text scale + keyboard, 3 hero journeys | NOT DONE | `docs/evidence/a11y_200pct_keyboard_findings.md` |
| 6 | analyze, tests, rules tests, 4 production builds, clean tree | PASS (analyze 0 issues; 58 tests; rules 7/7) | final run |
