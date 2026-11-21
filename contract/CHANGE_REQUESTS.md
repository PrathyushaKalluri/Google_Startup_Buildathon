# Contract Change Requests (`contract/CHANGE_REQUESTS.md`) — Triaged by Integrator (v1.1)

## CR-A-1 Test-only `text_in` WebSocket frame in `DEMO_MODE=true`
- **Status:** **ACCEPTED (Contract v1.1)**
- **Why:** Section 6.2 A4 requires a scripted WebSocket test harness (`services/live/tools/scripted_client.py`) that drives C03 deterministically without requiring live microphone audio on every CI run.
- **Resolution:** Added optional client-to-server frame `{"type":"text_in","text":"..."}` and `{"type":"simulate_go_away","seconds":30}` to Section C7 of `contract/SHARED_CONTRACT.md` (v1.1), enabled strictly when `DEMO_MODE=true` and rejected when `DEMO_MODE=false`. Both Part A (`services/live/bridge.py`) and Part B (`apps/kw_client/lib/src/live/live_call_client.dart`) support this frame.
