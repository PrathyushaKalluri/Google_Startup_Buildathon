---
name: firestore-stream-repository
description: Implement read-only Firestore stream repositories in apps/kw_client matching Keepwell Contract Section 6 paths, security rules, and offline persistence.
---

# Firestore Stream Repository (Keepwell)

Use this skill when building or modifying live Firestore listeners in `apps/kw_client`.

## 1. Contract Section 6 Paths (Read-Only)
Clients **never** write to Firestore (`allow write: if false`). All mutations go through the REST API (`kw_client` REST client).

| Path | Consumers | Notes |
|---|---|---|
| `centres/{cid}/tickets/{tid}` | `centre_admin`, `platform` | Ordered by `urgency_class`, `needed_by` |
| `centres/{cid}/conversations/{convId}` | `centre_admin`, `platform` | Active call/chat metadata |
| `centres/{cid}/conversations/{convId}/turns/{turnId}` | `centre_admin`, `platform` | Ordered by `at` ASC |
| `centres/{cid}/feed/{eventId}` | `centre_admin`, `platform` | Ordered by `at` DESC; unknown `type` falls back to generic row |
| `centres/{cid}/technicians/{tid}` | `centre_admin`, `platform`, own `technician` | Single doc read for technician role |
| `centres/{cid}/visits/{vid}` | `centre_admin`, `platform`, own `technician` | Technician queries MUST include `.where('technician_id', isEqualTo: techId)` |
| `centres/{cid}/parts_requests/{rid}` | `centre_admin`, `platform`, own `parts_centre` | Parts centre queries MUST include `.where('parts_centre_id', isEqualTo: pcId)` |
| `households/{hid}/whatsapp_thread/{mid}` | Household custom token (`household_id == hid`) | Ordered by `at` ASC |
| `meta/demo` | Any signed-in user | Active demo case & reset timestamp |

## 2. Implementation Rules
- **Match security rules in queries:** Firestore rules reject collection queries that are not constrained to the caller's claim (`technician_id`, `parts_centre_id`). Always add the exact `.where(...)` filter matching `infra/frontend/firestore.rules`.
- **Timestamps & Money:** Convert Firestore `Timestamp` to UTC `DateTime` in models; format to IST (`+05:30`) only at the UI layer. Keep money as integer paise (`*_paise`).
- **Schema resilience:** Ignore unknown fields from Part A gracefully; never throw on additive optional fields.
- **Offline persistence:** Enable Firestore persistence (`Settings(persistenceEnabled: true)`) for `apps/field` and expose `SnapshotMetadata.isFromCache` so the UI shows an honest offline/syncing indicator.
- **Error & degraded states:** Map `FirebaseException` (`permission-denied`, `unavailable`) into typed repository errors with retry streams; never leave a spinner hanging.
- **Emulator switching:** Configure `useFirestoreEmulator(host, port)` strictly from `--dart-define=FIRESTORE_EMULATOR_HOST` so switching to production is configuration-only.
