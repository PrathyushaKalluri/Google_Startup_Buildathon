---
description: Replay one of the 20 dataset cases (e.g. C03) through the real Keepwell backend pipeline and inspect live events.
---

# /play-case — Replay a Dataset Case

1. Identify the requested `case_id` (default `C03` — Hindi washing machine E21 at `c_fw`).
2. Confirm `kw-api` is healthy:
   ```bash
   curl -fsS http://127.0.0.1:8080/healthz
   ```
3. Trigger the case through the real intake pipeline (never a shortcut):
   ```bash
   curl -fsS -X POST http://127.0.0.1:8080/v1/admin/demo/play-case \
     -H "Content-Type: application/json" \
     -d '{"case_id":"C03"}'
   ```
4. For voice/video cases (`C03`), optionally run the scripted Live WebSocket client:
   ```bash
   python services/live/tools/scripted_client.py --case C03 --mode text_in
   ```
5. Fetch the resulting `TicketDetail` (`GET /v1/tickets/{id}`) and verify:
   - Urgency class, authority decision, and consent gates match the flow rules.
   - All expected Contract C8 live events were emitted to `centres/{cid}/feed`.
6. Report ticket ID, status, urgency, gates, fix attempt outcome, and assigned technician.
