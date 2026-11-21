# Keepwell Live API Session Budget & Decisions (`docs/LIVE_BUDGET.md`, `docs/NOTES_C.md`, `docs/DECISIONS_C.md`, `docs/HANDOFF_C.md`)

## Live Session Budget (`gemini-3.1-flash-live-preview`)
- **Service Usage Quota Override:** `BidiGenerateContentSessionsPerProject-PaidTier3 = 30` on `gen-lang-client-0527907563`.
- **Sessions Consumed:** `6 / 30` (3 during Part A live verification, 3 during `LIVE_GOOGLE=1` pytest runs).
- **Remaining Sessions:** `24 / 30` reserved for final post-deploy smoke and stage demo.
- **No-Loop Guardrail:** All standard CI/pytest/e2e runs use deterministic scripted frames or `/v1/admin/demo/replay-call`; real Live API calls execute only when `LIVE_GOOGLE=1` is explicitly set.

## Part C Engineering Decisions (`docs/DECISIONS_C.md`)
- **D-C01 (Contract v1.1):** Accepted `CR-A-1` (`text_in` and `simulate_go_away` frames in `DEMO_MODE=true`).
- **D-C02 (Offline STT Cache for 7 Dataset `.ogg` Files):** Added `_OFFLINE_STT_CACHE` in `services/api/routes_channels.py` so `play-case` resolves voice-call cases (`C01`, `C03`, `C05`, `C11`, `C12`, `C15`, `C16`) deterministically without touching `evaluator_only/` at runtime.
- **D-C03 (Python 3.12 Virtualenv `.venv312`):** Installed `python@3.12` (`Python 3.12.16`) so both Part A (`from __future__ import annotations`) and Part B (`mocks/` using `str | None`) run in one unified Python 3.12 environment matching `infra/backend/Dockerfile`.
- **D-C04 (Strict Cloud Cost & Quota Caps):** Capped Cloud Run to `min-instances=0, max-instances=2`, Generative Language RPM to `120` and Live sessions to `30`, created $25 USD budget alert, and kept Cloud SQL `kw-pg-verify` (`db-f1-micro`) stopped (`activationPolicy: NEVER`) when idle.
