.PHONY: help pub-get analyze test build-web mocks stage-demo gallery

API_BASE_URL ?= http://localhost:8081/v1
LIVE_WS_URL ?= ws://localhost:8082/v1/live/call
FIREBASE_PROJECT_ID ?= keepwell-demo
DEMO_MODE ?= true
PAYMENT_MODE ?= sandbox

DART_DEFINES := --dart-define=API_BASE_URL=$(API_BASE_URL) \
	--dart-define=LIVE_WS_URL=$(LIVE_WS_URL) \
	--dart-define=FIREBASE_PROJECT_ID=$(FIREBASE_PROJECT_ID) \
	--dart-define=DEMO_MODE=$(DEMO_MODE) \
	--dart-define=PAYMENT_MODE=$(PAYMENT_MODE)

help:
	@echo "Keepwell Part B (Experience Layer) — Dart Pub Workspace Targets"
	@echo "  make pub-get     Install workspace dependencies"
	@echo "  make analyze     Run dart/flutter analyze across all packages"
	@echo "  make test        Run all unit, widget, and golden tests"
	@echo "  make build-web   Build console, field, household, brand for web"
	@echo "  make mocks       Start Mock REST (8081) + Mock WS (8082)"
	@echo "  make stage-demo  Run C03 real-time time-lapse into Firestore emulator"
	@echo "  make gallery     Run kw_ui component gallery on Chrome"

pub-get:
	dart pub get

analyze:
	flutter analyze kw_ui kw_ui/example kw_client console field household brand

test:
	cd kw_client && dart test
	cd kw_ui && flutter test
	cd console && flutter test
	cd field && flutter test
	cd household && flutter test
	cd brand && flutter test

build-web:
	cd console && flutter build web $(DART_DEFINES)
	cd field && flutter build web $(DART_DEFINES)
	cd household && flutter build web $(DART_DEFINES)
	cd brand && flutter build web $(DART_DEFINES)

mocks:
	../keepwell/.venv/bin/python ../mocks/run_mocks.py

stage-demo:
	../keepwell/.venv/bin/python ../mocks/firestore/timelapse_c03.py

gallery:
	cd kw_ui/example && flutter run -d chrome
