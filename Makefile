# Keepwell Merged Repository Makefile (Part C — Integrator)
PYTHON := $(shell if [ -x ".venv312/bin/python" ]; then echo ".venv312/bin/python"; elif [ -x ".venv/bin/python3" ]; then echo ".venv/bin/python3"; else echo "python3"; fi)

.PHONY: setup up down seed test contract-test e2e eval lint build deploy smoke demo

setup:
	$(PYTHON) -m pip install -q -r services/requirements.txt
	cd apps && flutter pub get

up:
	docker compose up -d

down:
	docker compose down

seed:
	PYTHONPATH=. $(PYTHON) db/seed/load_seed.py

test:
	PYTHONPATH=. $(PYTHON) -m pytest -q db/tests services/agents/engines/tests services/api/tests evals/test_evals.py mocks/test_mocks.py
	cd apps && make test

contract-test:
	PYTHONPATH=. $(PYTHON) -m pytest -v e2e/contract

e2e:
	PYTHONPATH=. $(PYTHON) -m pytest -v e2e/contract e2e/journeys

eval:
	PYTHONPATH=. $(PYTHON) evals/eval_runner.py

lint:
	cd apps && flutter analyze kw_ui kw_ui/example kw_client console field household brand
	PYTHONPATH=. $(PYTHON) deploy/tools/check_ownership.py

build:
	cd apps && ./tools/build_all.sh

deploy:
	./deploy/deploy_all.sh

smoke:
	PYTHONPATH=. $(PYTHON) deploy/tools/smoke_test.py

demo:
	PYTHONPATH=. $(PYTHON) services/live/tools/scripted_client.py
