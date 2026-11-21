# Firebase App Check Setup (Keepwell Frontend)

Firebase App Check protects Firestore and the Keepwell Cloud Run API (`kw-api`) from non-app traffic across all four web surfaces (`console`, `field`, `household`, `brand`) and the Android technician build (`field`).

## 1. Web Provider: reCAPTCHA Enterprise

1. In Google Cloud Console (project `GCP_PROJECT_ID`, region `asia-south1`), enable the **reCAPTCHA Enterprise API**.
2. Create one **score-based (checkboxless)** reCAPTCHA Enterprise web key per Hosting domain (or a single key covering all four Hosting domains: `keepwell-console.web.app`, `keepwell-field.web.app`, `keepwell-household.web.app`, `keepwell-brand.web.app`, plus any custom domains).
3. In Firebase Console -> **App Check** -> **Apps**:
   - Register each of the four Web apps (`console`, `field`, `household`, `brand`) with **reCAPTCHA Enterprise** using the site key from step 2.
   - Set token TTL to `1 hour` (default).
4. Pass the site key at build time via `--dart-define`:

```bash
flutter build web \
  --dart-define=FIREBASE_PROJECT_ID=$FIREBASE_PROJECT_ID \
  --dart-define=APP_CHECK_RECAPTCHA_KEY=$APP_CHECK_RECAPTCHA_KEY \
  --dart-define=API_BASE_URL=$API_BASE_URL \
  --dart-define=LIVE_WS_URL=$LIVE_WS_URL
```

5. Activate in Flutter (`apps/kw_client` bootstrap) before opening any Firestore listener or REST call:

```dart
await FirebaseAppCheck.instance.activate(
  webProvider: ReCaptchaEnterpriseProvider(recaptchaSiteKey),
  androidProvider: kDebugMode
      ? AndroidProvider.debug
      : AndroidProvider.playIntegrity,
);
```

## 2. Android Provider (`apps/field`)

1. Register `apps/field` Android SHA-256 signing fingerprints (debug and release) in Firebase Console -> **Project settings** -> **Your apps**.
2. Register the Android app in **App Check** with **Play Integrity**.

## 3. Local Emulator & Debug Token

When running against the Firebase Emulator Suite (`infra/frontend/firebase.json`) or in `flutter run -d chrome` during development:

1. In `web/index.html` (only when `DEMO_MODE=true` or local dev), or before `FirebaseAppCheck.instance.activate`, set the debug token flag:

```html
<script>
  if (location.hostname === 'localhost' || location.hostname === '127.0.0.1') {
    self.FIREBASE_APPCHECK_DEBUG_TOKEN = true;
  }
</script>
```

2. On first launch, copy the debug token printed in the browser console (`App Check debug token: <uuid>`) and register it in Firebase Console -> **App Check** -> **Apps** -> **Manage debug tokens** (only needed when pointing at a live Firebase project; the local Firestore emulator does not enforce App Check tokens).
3. For CI runs against a staging Firebase project, store a dedicated debug token in Secret Manager and inject it via `--dart-define=APP_CHECK_DEBUG_TOKEN=<token>` (never commit a debug token to the repo).

## 4. API Verification & Enforcement Rollout

1. **Client header:** `kw_client` attaches `X-Firebase-AppCheck: <token>` (from `FirebaseAppCheck.instance.getToken()`) on every REST request to `kw-api` when not in mock mode.
2. **Rollout:**
   - Start Firestore App Check in **Unenforced (Metrics)** mode until all four Hosting targets report >99% verified requests.
   - Switch Firestore to **Enforced** in Firebase Console -> **App Check** -> **APIs** -> **Cloud Firestore**.
   - Keep `kw-api` verification configurable so local mocks and emulator tests run without live reCAPTCHA calls.
