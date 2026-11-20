---
name: rls-and-auth
description: PostgreSQL Row-Level Security (kw_app), Firebase Auth custom claims, household magic links, brand/retailer API keys, and PII protection in Keepwell.
---

# RLS, Auth & Privacy (`services/common/`, `db/`)

## Database Isolation (RLS)
1. The application always connects as role `kw_app` (never `NOBYPASSRLS`).
2. Every request opens one transaction and sets local session context before any query:
   - Centre/technician requests: `SET LOCAL kw.centre_id = '<claim_uuid>'`
   - Platform/cross-centre jobs: `SET LOCAL kw.role = 'platform'`
3. Cross-centre appliance history is accessed **only** via `read_shared_history(appliance_id, centre_id, ticket_id, reason)`, which verifies `share_technical_history` consent and inserts an immutable `access_log` row.
4. Technician contact reveal (`GET /v1/visits/{id}`) releases household address and phone only when the slot is confirmed and logs every read to `access_log`.

## Authentication Surfaces (Contract C3)
- **Console / Technician / Parts / Brand / Platform:** `Authorization: Bearer <Firebase ID token>`. Verify token and extract claims: `role`, `centre_id`, `technician_id`, `parts_centre_id`, `brand_id`.
- **Household (zero-login):** Signed, expiring, single-purpose magic tokens (`MAGIC_LINK_SIGNING_KEY`). `POST /v1/public/session` exchanges a valid magic token for a scoped Firebase custom token (`household_id` claim) to read Firestore `whatsapp_thread`.
- **Brand & Retailer webhooks:** `X-Keepwell-Key` header mapped to brand/retailer identity.
- **WhatsApp & Payment webhooks:** Verify HMAC signatures (`WHATSAPP_APP_SECRET`, `PAYMENT_WEBHOOK_SECRET`).

## PII Rules
- Store phone numbers as keyed HMAC hashes (`PHONE_HASH_KEY`) + masked display; never log raw phones, addresses, or OTP codes.
- Always run `pytest db/tests/test_rls.py` after any schema or auth change.
