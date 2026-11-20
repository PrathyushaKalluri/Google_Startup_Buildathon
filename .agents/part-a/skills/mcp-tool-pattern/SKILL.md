---
name: mcp-tool-pattern
description: Rules for implementing and registering tools on Keepwell's Streamable HTTP MCP server mounted at /mcp inside kw-api.
---

# MCP Tool Pattern (`services/mcp/`)

## Architecture
- Keepwell mounts a Streamable HTTP MCP server at `/mcp` inside `kw-api`.
- Both ADK agents and the Gemini Live bridge call tools through `/mcp` or the exact same underlying Python tool functions.

## Checklist for Every MCP Tool
1. **Pydantic v2 I/O:** Validate all arguments and return a compact, deterministic JSON-serializable dict that fits cleanly in an LLM context window.
2. **RLS context:** Execute every database operation inside a single transaction using the caller's RLS context (`SET LOCAL kw.centre_id = '<claim>'` or `SET LOCAL kw.role = 'platform'`). Never bypass RLS with a superuser role.
3. **Idempotency:** Write tools (`create_or_update_ticket`, `record_gate`, `start_fix_attempt`, `issue_quote`, `send_message`, `request_closure_otp`, etc.) must be safe to retry (upsert or idempotency key).
4. **Live event emission:** Every state-changing tool writes the corresponding Contract C8 event to the Postgres outbox (drained to Firestore `centres/{cid}/feed` by `kw-worker`) in the **same DB transaction**—never dual-write directly to Firestore.
5. **Engine delegation:** Tools wrap deterministic engines (`authority`, `urgency`, `gates`, `safefix`, `parts`, `planner`, `assignment`, `pricing`, `otp`) rather than re-implementing business rules.
6. **Error shape:** Return structured, actionable error codes (`authority_failed`, `gate_not_satisfied`, `part_unresolved`, `safety_blocked`) so the agent can recover cleanly without hallucinating.
