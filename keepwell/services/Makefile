VENV_BIN := $(shell if [ -d "../.venv" ]; then echo "../.venv/bin/"; fi)
PYTHON := $(VENV_BIN)python3
PYTEST := $(VENV_BIN)pytest

.PHONY: db-up seed test rls-test eval api worker contract-check openapi

db-up:
	docker compose -f ../infra/backend/docker-compose.dev.yml up -d

seed:
	cd .. && $(PYTHON) db/seed/load_seed.py

rls-test:
	cd .. && $(PYTEST) -v db/tests/test_rls.py

test:
	cd .. && $(PYTEST) -v db/tests/ services/ evals/

eval:
	cd .. && $(PYTHON) evals/eval_runner.py

api:
	cd .. && $(VENV_BIN)uvicorn services.api.main:app --host 0.0.0.0 --port 8000 --reload

worker:
	cd .. && $(VENV_BIN)uvicorn services.worker.main:app --host 0.0.0.0 --port 8001 --reload

openapi:
	cd .. && $(PYTHON) -c "import json; from services.api.main import app; open('services/api/openapi.json','w').write(json.dumps(app.openapi(), indent=2))"

contract-check:
	cd .. && $(PYTEST) -v services/api/tests/test_contract.py
