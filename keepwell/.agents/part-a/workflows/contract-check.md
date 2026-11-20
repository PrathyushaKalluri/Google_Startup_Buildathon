---
description: Validate Part A against the frozen Shared Contract (OpenAPI, RLS isolation, engine unit tests, and contract tests).
---

# /contract-check — Verify Frozen Contract Compliance

1. Run deterministic engine unit tests and parts-never-invented fuzz test:
   ```bash
   pytest services/agents/engines/
   ```
2. Run PostgreSQL Row-Level Security isolation tests (`kw_app` cannot read another centre's rows):
   ```bash
   pytest db/tests/test_rls.py
   ```
3. Run REST API & WebSocket contract tests and validate `services/api/openapi.json` against Contract C5:
   ```bash
   pytest services/api/tests/
   ```
4. Confirm zero forbidden terms (`staff`, `dispatcher`, `human approval`) in Part A user-facing copy and zero secrets committed:
   ```bash
   git status --short
   ```
5. Report pass/fail counts for each suite and flag any contract drift.
