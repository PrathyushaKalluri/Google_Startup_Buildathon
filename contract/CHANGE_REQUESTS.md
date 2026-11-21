# Contract Change Requests (`contract/CHANGE_REQUESTS.md`)

No breaking changes required by Part A (`part-a/agent-core`). All endpoints, Firestore paths, live events, and WebSocket frames match `contract/SHARED_CONTRACT.md` verbatim.

## CR-A-1 Test-only `text_in` WebSocket frame in `DEMO_MODE=true`
- **Why:** Section 6.2 A4 requires a scripted WebSocket test harness (`services/live/tools/scripted_client.py`) that drives C03 deterministically without requiring live microphone audio.
- **Proposed text:** Add optional client-to-server frame `{"type":"text_in","text":"..."}` to Section C7, enabled strictly when `DEMO_MODE=true`.
- **What I assumed meanwhile:** Implemented as an additive frame gated behind `settings.demo_mode`, ignored/rejected with `403`/`forbidden` error frame when `DEMO_MODE=false`.
