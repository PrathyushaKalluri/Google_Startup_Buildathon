# Keepwell Operations Runbook & Rollback (`docs/RUNBOOK.md`, `docs/SECURITY.md`, `docs/KNOWN_ISSUES.md`, `docs/LIVE_BUDGET.md`)

## 1. Rollback Procedure
- **Cloud Run (`kw-api` / `kw-worker`):**
  ```bash
  PREV_REV=$(gcloud run revisions list --service=kw-api --region=asia-south1 --project=gen-lang-client-0527907563 --format="value(name)" --limit=2 | tail -1)
  gcloud run services update-traffic kw-api --to-revisions="${PREV_REV}=100" --region=asia-south1 --project=gen-lang-client-0527907563
  ```
- **Firebase Hosting (4 sites):**
  ```bash
  firebase hosting:clone kw-console-0527:<prev-version> kw-console-0527:live --project gen-lang-client-0527907563
  ```
- **Database & Demo State Reset:**
  ```bash
  curl -X POST "${API_BASE_URL}/admin/demo/reset" -H "Authorization: Bearer demo:platform@keepwell.demo"
  curl -X POST "${API_BASE_URL}/admin/projection/rebuild" -H "Authorization: Bearer demo:platform@keepwell.demo"
  ```

## 2. Live API Session Budget Tracker
- **Hard Ceiling:** 30 real `gemini-3.1-flash-live-preview` sessions enforced both by Service Usage quota override (`BidiGenerateContentSessionsPerProject-PaidTier3 = 30`) and by gating live tests behind `LIVE_GOOGLE=1`.
- **Sessions Used to Date:** **6 / 30** (Part A smoke + `LIVE_GOOGLE=1` pytest verification runs).
- **Remaining Budget for Stage Rehearsal & Demo:** **24 / 30** sessions.
- **Zero-Cost Fallback:** `POST /v1/admin/demo/replay-call` replays the full C03 event stream deterministically without opening a Live API session.

## 3. Known Issues & Mitigations
1. **Local PG 18 vs Cloud SQL PG 16:** macOS Homebrew bottles `postgis` and `pgvector` for PostgreSQL 18, while Cloud SQL runs PostgreSQL 16.15. *Mitigation:* `input/docs/keepwell_schema.sql` and `001_part_a_additions.sql` are verified unmodified on both local PostgreSQL 18.7 and Cloud SQL PostgreSQL 16.15.
2. **Cold-start on `min-instances=0`:** Because cost guardrails set `--min-instances=0`, the first request after idle takes ~2–4s. *Mitigation:* Run `make smoke` 60 seconds before the stage presentation to warm `kw-api`.
