Read `docs/HANDOVER.md` completely first. Do not modify any files or run any paid Google Cloud or live model calls yet.

1. Verify the repository state by running `git status`, `git branch -a`, `git log --oneline -5`, and `/opt/homebrew/bin/gcloud sql instances list --project=gen-lang-client-0527907563`.
2. Run the offline verification suite (`PYTHONPATH=. .venv312/bin/python -m pytest -q db/tests services/agents/engines/tests services/api/tests evals/test_evals.py mocks/test_mocks.py e2e/contract e2e/journeys`) and `PYTHONPATH=. .venv312/bin/python deploy/tools/smoke_test.py` to confirm all tests pass.
3. Summarise where we are in five lines (current branch, test status, GCP cost/resource state, and the pending C6 deploy step) and wait for my instruction before changing anything.
