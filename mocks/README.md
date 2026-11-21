# Keepwell Part B Mocks

Contract-exact local mock servers and Firestore emulator fixtures for developing and testing all four Keepwell Flutter apps (`console`, `field`, `household`, `brand`) without requiring Part A's live backend.

## Components

| Path | Port / Target | Purpose |
|---|---|---|
| `mocks/fixtures/build_fixtures.py` | `mocks/fixtures/generated/` | Builds normalized JSON fixtures from the real simulation dataset (`input/dataset/` or `keepwell/docs_v1/keepwell_sim_dataset_v0.2.zip`). |
| `mocks/rest/server.py` | `http://localhost:8081` | FastAPI mock REST API implementing every endpoint in `SHARED_CONTRACT.md` §5, cursor pagination, stateful mutations, CORS, and `X-Mock-Fail: <status>` error injection. |
| `mocks/ws/server.py` | `ws://localhost:8082/v1/live/call` | Mock Live Call WebSocket server implementing `SHARED_CONTRACT.md` §7 with C03 Hindi/English + video replay mode and standalone `language_hint: "echo"` mode. |
| `mocks/firestore/seed_emulator.py` | `FIRESTORE_EMULATOR_HOST` (`localhost:8080`) | Seeds Firestore emulator via REST API (zero extra SDK dependencies) with all 9 centres, 20 tickets, technicians, visits, parts requests, WhatsApp threads, `meta/demo`, and 5 C03 point-in-time snapshots. |
| `mocks/firestore/timelapse_c03.py` | `FIRESTORE_EMULATOR_HOST` (`localhost:8080`) | Streams the full C03 stage event sequence into Firestore emulator over ~25 seconds (configurable `--delay`). |
| `mocks/test_mocks.py` | pytest | End-to-end automated verification of fixtures, REST API, WebSocket replay/echo, and Firestore serialization. |

## Quick Start (One Command)

From the repository root:

```bash
# 1. Build fixtures from the real simulation dataset
keepwell/.venv/bin/python -m mocks.fixtures.build_fixtures

# 2. Run REST (8081) and WebSocket (8082) mock servers together
(keepwell/.venv/bin/uvicorn mocks.rest.server:app --port 8081 & keepwell/.venv/bin/uvicorn mocks.ws.server:app --port 8082 & wait)
```

## Firestore Emulator Seeding & C03 Time-Lapse

With the Firebase Firestore emulator running on `localhost:8080`:

```bash
# Seed all 9 centres, 20 cases, WhatsApp threads, and C03 snapshots
keepwell/.venv/bin/python -m mocks.firestore.seed_emulator

# Play the live C03 stage time-lapse (~25s)
keepwell/.venv/bin/python -m mocks.firestore.timelapse_c03 --delay 0.85
```

## Error Injection

Send header `X-Mock-Fail: 503` (or any HTTP status code) to any REST endpoint to verify client error banners and retry states:

```bash
curl -i -H "X-Mock-Fail: 503" http://localhost:8081/v1/tickets
```

## Run Automated Verification

```bash
keepwell/.venv/bin/pytest mocks/test_mocks.py -v
```
