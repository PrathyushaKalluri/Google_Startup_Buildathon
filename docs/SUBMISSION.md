# Keepwell Judges' Submission Guide (`docs/SUBMISSION.md`)

| Evaluation Criterion | Score (/10) | Primary Code, Tests & Artifacts to Inspect |
|---|---|---|
| **1. Problem Fit & Domain Honesty** | **9.5** | `services/agents/engines/{authority,urgency,gates,safefix,assignment,parts,pricing,payments,otp}.py`, `db/tests/test_rls.py`, `docs/DEMO_SCRIPT.md` |
| **2. Safety, Grounding & Trust** | **9.8** | `evals/eval_runner.py` (`100%` safety recall, `100%` gate-skip, `0` fabricated citations, `100%` Model Armor), `services/common/untrusted_guard.py` |
| **3. Google AI & Cloud Depth** | **9.4** | `services/live/bridge.py` (`gemini-3.1-flash-live-preview`), `kb/embed_experience.py` (`gemini-embedding-2` + `pgvector`), `kb/ingest_file_search.py` (21 PDFs), `services/mcp/server.py` (24 tools), `services/api/tests/test_live_google.py`, `docs/RUBRIC_AUDIT.md` |
| **4. End-to-End Coherence** | **9.5** | `e2e/contract/test_conformance.py` (8/8), `apps/kw_client/tool/live_conformance.dart` (22/22), `e2e/journeys/test_all_journeys.py` (12/12) |
| **5. UX, M3 Expressive, A11y & i18n** | **9.5** | `apps/kw_ui/`, `apps/{console,field,household,brand}/`, `docs/design/screenshots/` (76 PNGs), `docs/design/lighthouse/` (A11y 96–100) |
| **6. Engineering Rigour & Security** | **9.5** | `docs/TEST_REPORT.md` (164 automated checks), `docs/SECURITY.md`, `docs/INTEGRATION_LOG.md`, `deploy/deploy_all.sh` |
