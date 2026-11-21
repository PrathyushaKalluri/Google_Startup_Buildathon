---
description: Start all Keepwell Part B mock servers (REST, WebSocket C03 replay, Firestore & Auth emulators) and verify health.
---

# /mocks — Start Local Mock Stack

1. Check prerequisites (`python3` or `dart`, `firebase` CLI, `node`).
2. Start the full mock stack from `apps/` or repo root:
   ```bash
   make mocks
   ```
   This launches:
   - Mock REST API (`/v1/*` + `/healthz`) seeded from `input/dataset/csv/`
   - Mock WebSocket server (`WS /v1/live/call`) with C03 script replay & echo mode
   - Firebase Emulators (`infra/frontend/firebase.json`: Auth `9099`, Firestore `8080`, Hosting `5000`, UI `4000`)
3. Load Firestore emulator fixtures from `mocks/firestore/` if not auto-loaded by `make mocks`.
4. Verify services are healthy:
   ```bash
   curl -sf http://127.0.0.1:8000/healthz
   curl -sf http://127.0.0.1:8080/ >/dev/null && echo "Firestore emulator OK"
   ```
5. To stop all mock processes cleanly, run `Ctrl+C` or `make mocks-stop`.
