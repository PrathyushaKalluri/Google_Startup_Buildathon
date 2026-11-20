---
name: gemini-live-bridge
description: Implementing and maintaining the WS /v1/live/call bridge to Gemini Live API with native audio, video frames, tool calling, context compression, session resumption, and GoAway handling.
---

# Gemini Live API Bridge (`services/live/`)

## Protocol (Contract C7)
- **Endpoint:** `WS /v1/live/call?token=<Firebase ID token | demo household token>`
- **Audio:** Client sends raw PCM16 LE, 16 kHz, mono (20–100 ms chunks); server streams raw PCM16, 24 kHz, mono.
- **Video/Images:** Client sends `video_frame` (~1 fps, max 640 px) and `image` (sticker/display) as base64 JPEG JSON frames.
- **Resuming to video:** `send_video_link` mints a signed `/v/<token>` link; when opened, the client reconnects with `resume_conversation_id` and `client_state.modality="video"`, continuing the **same conversation and ticket**.

## Reliability & Session Limits
Gemini Live sessions cap at ~15 min (audio-only) and ~2 min (audio+video) without compression:
1. Always enable **context-window compression** (`sliding_window`) and **session resumption** on every Live session.
2. Persist the latest resumption handle per `conversation_id`.
3. On server `GoAway` or transient disconnect: emit `{"type":"go_away","seconds":N}` to the client, transparently reconnect using the resumption handle, and keep the client WebSocket open.
4. **File Search limitation:** File Search cannot run natively inside the Live API; expose `search_manuals` as a function-calling tool that queries the File Search store via the standard Gemini API.
5. **System prompt:** Keep `services/live/prompts/live_agent.md` under 120 lines; enforce recording notice first, verbatim Gate 1 & Gate 2, safety-first, and no unverified prices/slots.
6. **Fallback & testing:** Support `{"type":"text_in"}` only when `DEMO_MODE=true` for `services/live/tools/scripted_client.py`, and keep `/v1/admin/demo/replay-call` working for Live API outages.
