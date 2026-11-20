---
name: firestore-projection
description: Outbox-driven projection of Postgres state and live events to Firestore paths in Contract C6 and C8, plus idempotent full rebuilds.
---

# Firestore Live Projection (`services/worker/`, `services/api/`)

## Architecture (No Dual Writes)
- Postgres is the single source of truth. Never write directly to Firestore from an API handler outside the outbox pattern.
- Every committed state mutation inserts a row into the Postgres outbox table (and optionally publishes to Pub/Sub `kw-projections`). `kw-worker` drains the outbox and upserts the exact Firestore documents in Contract C6 and C8.
- Document IDs are always the Postgres UUID strings; timestamps are Firestore `Timestamp`.

## Projected Paths (Contract C6)
- `centres/{centre_id}/tickets/{ticket_id}` — `TicketCard` + `unread`, `last_event_at`, `assignee`, `next_action`, `payment_status`
- `centres/{centre_id}/conversations/{conversation_id}` + `turns/{turn_id}`
- `centres/{centre_id}/feed/{event_id}` — Contract C8 live events (`{id, at, centre_id, ticket_id, conversation_id, type, actor, title, detail, payload}`)
- `centres/{centre_id}/technicians/{technician_id}`
- `centres/{centre_id}/visits/{visit_id}`
- `centres/{centre_id}/parts_requests/{id}`
- `households/{household_id}/whatsapp_thread/{message_id}`
- `meta/demo` — `{active_case_id, reset_at}`

## Idempotent Rebuild
- `POST /v1/admin/projection/rebuild` clears and replays all Firestore documents from Postgres.
- Verify idempotency: running rebuild twice produces identical Firestore state with no duplicate feed events or orphaned docs.
- Never write raw PII (unmasked phone numbers or raw OTP codes) into Firestore feed documents.
