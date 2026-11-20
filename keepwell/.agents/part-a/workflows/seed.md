---
description: Start the local Postgres + Firebase emulator stack and idempotently load the Keepwell seed dataset.
---

# /seed — Reset & Load Seeded World

1. Ensure the local dev stack is running:
   ```bash
   docker compose -f infra/backend/docker-compose.dev.yml up -d
   ```
2. Wait for Postgres (`keepwell-postgres`) and Firebase emulators (`9099`, `8080`) to report healthy.
3. Run the idempotent seed loader (loads `input/dataset/csv/*`, creates `kw_app` RLS role, resets app-output tables):
   ```bash
   python db/seed/load_seed.py --reset
   ```
4. Verify row counts match `input/dataset/manifest.json` (9 centres, 165 households, 341 appliances, 395 historical tickets).
5. Rebuild Firestore projections from Postgres (if `kw-api` is running):
   ```bash
   curl -fsS -X POST http://127.0.0.1:8080/v1/admin/projection/rebuild
   ```
6. Report loaded row counts and any errors.
