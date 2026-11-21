# Keepwell Security Posture (`docs/SECURITY.md`)

1. **Row-Level Security (`kw_app`):** Non-superuser PostgreSQL role (`rolsuper=false`, `rolbypassrls=false`). Every transaction sets `SET LOCAL kw.centre_id` or `SET LOCAL kw.role = 'platform'`. Cross-centre reads return `0` rows; cross-centre inserts raise `InsufficientPrivilege`.
2. **Consent-Gated Shared History:** Cross-centre appliance history is accessible only via `kw.read_shared_history()`, which checks `consent_ledger` and appends an immutable `access_log` row.
3. **Regional Model Armor (`asia-south1`):** Template `projects/gen-lang-client-0527907563/locations/asia-south1/templates/keepwell-guard-v1` (`dataResidencyCompliant: true`) screens inbound/outbound text with deterministic regex outage fallback.
4. **Firebase Auth & Single-Purpose Magic Links:** `firebase_admin.auth.verify_id_token()` verifies 3-segment JWTs; `demo:` and unsigned emulator tokens are rejected when `DEMO_MODE=false` and `FIREBASE_AUTH_EMULATOR_HOST` is unset.
5. **Firestore Security Rules (`infra/frontend/firestore.rules`):** `allow write: if false` on every path; centre isolation enforced via `request.auth.token.centre_id == cid`; household thread isolated via `request.auth.token.household_id == hid`.
6. **Secrets & Privacy:** Phone numbers are HMAC-SHA256 hashed (`PHONE_HASH_KEY`) + AES-encrypted with masked display; technician address/phone released only after slot confirmation and logged in `access_log`; raw media deleted after 48h (`enforce_media_retention`); zero secrets tracked in git.
