# MASTER BUILD PROMPT — CIRCUIT

You are the lead software engineer implementing Circuit. Build runnable software; do not write another strategy proposal.

## Read first
Read all Markdown files in this archive. Treat:
1. `02_MENTOR_BUILD_READY_DESIGN.md`
2. this file
3. `04_RUNTIME_SYSTEM_PROMPT.md`
4. `05_TRIGGER_AND_WHATSAPP_FLOW.md`
5. `06_RAG_AND_KNOWLEDGE_RAIL.md`
6. `07_INTEGRATIONS_GNANI_PINE_DELHIVERY.md`
7. `08_IMPLEMENTATION_CONTRACTS.md`
8. `09_RECORDING_PLAN.md`
9. `10_DECISIONS_AND_CONFLICTS.md`
as authoritative.

## Model setup
Ask once: **Gemini or Claude?** No comparisons or automatic switching. Read provider/model ID and API key from private environment variables. If unavailable, stop with a setup-blocked status; never invent a current model ID or secret.

## Technology
Python 3.11+, FastAPI, Pydantic, SQLite, FTS5, httpx, durable SQLite job/outbox table or similarly persistent worker, simple server-rendered trace viewer.

Do not add:
- consumer app;
- phone/SIP;
- Gmail/Calendar/Sheets;
- KaryaFlow dependency;
- multi-agent framework;
- microservices;
- model benchmark;
- vector DB unless it solves a demonstrated retrieval need.

## Build order
1. Config, migrations, S0–S11 case/event ledger, actor roles, synthetic fixture loader, trace screen.
2. Meta GET verification + signed POST webhook + dedupe + media download.
3. Real Gnani STT adapter; wait for actual transcript before voice reasoning.
4. One LLM tool loop with `04_RUNTIME_SYSTEM_PROMPT.md`.
5. Mistri Gyan FTS5 ingestion and citations; Machine Kundli store; agency operational DB.
6. Technician ranking, agency assignment, household slot choice, quotes and S5 deterministic gate.
7. Pine/Delhivery documentation-simulated world-event adapters; never auto-return a successful fake response.
8. Later field events, S8 role-play distinction, S9 future-event handling, S10 correction and S11 review queue.
9. Full offline tests, then credential-gated live tests.
10. Five-minute trace export.

## Trigger contract
Customer WhatsApp webhook creates/resumes case. A system prompt never triggers itself. CLI starts the server/tests only.

For audio:
Meta webhook → persist `AWAITING_STT` → fetch media → validate duration/codec → call Gnani once → persist exact result → resume model.

## Truth rules
- Real WhatsApp transport can carry **ROLEPLAY** facts.
- `DOC_SIMULATED` Pine/Delhivery replies are not network traffic.
- Synthetic stock is not physical custody.
- Generic manuals do not prove a part SKU.
- `CREATED` payment status is not approved/paid.
- Role-play field proof is not a real repaired AC.
- S9 cannot time-travel.
- Historical research anecdotes are not diagnostic priors unless appropriately reviewed/validated.
- No hidden chain-of-thought export; log concise rule IDs and decision summary only.

## S5 gate
A repair-ready outcome requires all applicable evidence:
entitlement, safety, diagnostic adequacy, technician skill, agency assignment, technician acceptance, customer slot, resident access, part compatibility, kit custody, payer permission, appropriate simulated authorization, pilot owner signoff, feasible route.

Missing exact part evidence → inspection-only.

## Gnani budget
Use real Gnani only. Max 60s REST input. Add configurable internal per-case/demo call budgets and idempotent caching. On 403/429/credit exhaustion, ask user for text rather than fabricating transcription.

## Required outputs
- runnable repository;
- README and commands;
- `.env.example` with blank secrets;
- migrations/schema;
- tests;
- redacted sample trace;
- `BUILT / TESTED / BLOCKED / NEXT MANUAL ACTION / RECORDING READY?` report.

Never claim live integration unless it actually ran.
