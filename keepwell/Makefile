.PHONY: dev test eval seed deploy clean help

help:
	@echo "KeepWell Buildathon Commands:"
	@echo "  make dev      - Start local development server with auto-reload"
	@echo "  make seed     - Populate database with fixtures and seed appliances"
	@echo "  make test     - Run unit and integration tests"
	@echo "  make eval     - Run 100-case evaluation harness against release gates"
	@echo "  make deploy   - Deploy KeepWell to Google Cloud Run (asia-south1)"

dev:
	python3 run.py

seed:
	python3 -m app.fixtures.seed_data

test:
	pytest -v tests/

eval:
	python3 evals/eval_runner.py

deploy:
	cd deploy && ./setup_gcp.sh

clean:
	rm -f keepwell.db
	rm -rf __pycache__ .pytest_cache
