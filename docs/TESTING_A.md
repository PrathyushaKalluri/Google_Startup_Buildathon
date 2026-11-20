# Part A Testing Guide (`docs/TESTING_A.md`)

## Test Suites
```bash
cd keepwell
# 1. Seed & RLS isolation tests (A1)
.venv/bin/pytest -v db/tests/test_rls.py

# 2. 10 Deterministic engines + 50-part fuzz test + 100% safety recall (A2)
.venv/bin/pytest -v services/agents/engines/tests/test_engines.py

# 3. Full REST API v1 contract tests + C03 Live WebSocket scripted run (A4/A5)
.venv/bin/pytest -v services/api/tests/test_contract.py

# 4. 20-case dataset + 100-case synthetic eval harness & 5 release gates (A6)
.venv/bin/python evals/eval_runner.py
.venv/bin/pytest -v evals/test_evals.py
```

## Live WebSocket Test-Only Frames (`DEMO_MODE=true`)
When `DEMO_MODE=true`, `WS /v1/live/call` accepts two additive test frames:
- `{"type": "text_in", "text": "..."}` — feeds a household utterance as transcribed speech through Model Armor and the Live orchestrator.
- `{"type": "simulate_go_away", "seconds": 30}` — triggers a `go_away` frame followed by transparent session resumption (`ready`).

Both frames are rejected when `DEMO_MODE=false`.
