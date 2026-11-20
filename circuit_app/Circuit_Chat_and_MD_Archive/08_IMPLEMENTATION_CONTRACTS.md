# Implementation contracts

## Core data responsibilities

### Case ledger
`cases`, `actor_roles`, `inbound_events`, `outbound_messages`, `event_jobs`, `agent_decisions`, `connector_calls`, `payer_approvals`, `owner_approvals`, `repair_proofs`, `future_followups`.

### Machine Kundli
`machines`, `machine_consents`, `machine_events`.

### Mistri Gyan
`knowledge_sources`, `knowledge_chunks`, `fault_tests`, `part_compatibility_evidence`, `knowledge_review_queue`.

### Agency data
`agencies`, `agency_policies`, `agency_contacts`, `technicians`, `technician_skills`, `technician_shifts`, `appointment_slots`, `assignments`, `inventory_items`, `inventory_reservations`, `kit_custody_events`, `price_rules`, `quotes`.

All tables are tenant-scoped where appropriate.

## Internal event example

```json
{
  "event_id": "uuid",
  "provider_event_id": "wamid-or-roleplay-id",
  "agency_id": "AGENCY-DEMO-01",
  "case_id": "generated-after-first-message",
  "actor_role": "household_reporter",
  "event_type": "audio_received",
  "source_mode": "ROLEPLAY",
  "transport_mode": "LIVE_WHATSAPP",
  "occurred_at": "source timestamp",
  "payload_ref": "restricted raw artifact",
  "media_sha256": "measured hash"
}
```

A role-playing participant can use **live WhatsApp transport**. That does not turn fictional AC facts into verified field evidence.

## Model decision shape

```json
{
  "state": "S2",
  "next_action": "ask_followup",
  "selected_tool": "send_whatsapp",
  "recipient_role": "household_reporter",
  "proposed_text": "Could you send the model-label photo without removing any panel?",
  "rule_ids": ["R03", "R04", "R05"],
  "evidence_refs": ["chunk-id"],
  "brief_explanation": "Exact model is unknown; part selection is unsafe."
}
```

Backend validates:
- tool allowed in current state;
- recipient;
- permissions;
- source references;
- transition;
- spending/safety;
- maximum tool rounds;
- tenant ownership.

## S5 gate outputs

Do not return a single unexplained `ready=true`.

Return:
- predicate;
- pass/fail/unknown;
- evidence reference;
- source label;
- reason.

Possible top-level verdict:
- `READY_IN_ROLEPLAY`;
- `NEEDS_INSPECTION`;
- `WAIT_FOR_AUTHORIZATION`;
- `WAIT_FOR_KIT`;
- `WAIT_FOR_TECHNICIAN`;
- `OEM_REFERRAL`;
- `ESCALATE_SAFETY`.

A completely fictional model/kit can test logic only; it cannot certify real physical readiness.

## Idempotency

- Meta message ID dedupe.
- Audio hash + message ID Gnani cache.
- Partner simulation event unique IDs.
- Outbox exactly-once logical intent with safe retries.
- Never retry a financial/debit operation blindly.

## Security

- secrets only in local env/secret manager;
- no tokens in trace;
- public trace redacts numbers/address;
- restricted raw evidence preserved separately;
- signature validation before webhook parsing;
- tenant isolation;
- role-based read/write access;
- retention/consent policy for audio/photos/device identifiers.
