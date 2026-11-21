---
name: live-call-client
description: Implement and maintain the WS /v1/live/call voice and video client in apps/kw_client, apps/household, and apps/console per Contract Section 7.
---

# Live Call Client (`WS /v1/live/call`)

Use this skill when building or debugging the voice dialer, video-link page (`/v/<token>`), or console test-call sheet.

## 1. Connection & Auth
- Connect to `$LIVE_WS_URL/v1/live/call?token=<Firebase ID token | demo household token>`.
- Immediately send the `start` text frame:
  `{"type":"start","centre_key":"c_fw","caller_number":"+91 ...","language_hint":null,"resume_conversation_id":null}`
- Wait for `{"type":"ready","conversation_id":"...","session_id":"...","centre_name":"...","recording_notice":"..."}` and display `recording_notice` verbatim at call start.

## 2. Audio Pipeline (Voice & Barge-In)
- **Mic upload (binary frames):** raw PCM16 little-endian, `16 kHz`, mono, `20–100 ms` chunks. Request mic permission with a plain-language explanation; show a clear recovery state if denied.
- **Agent playback (binary frames):** raw PCM16, `24 kHz`, mono. Feed through a small jitter buffer with browser echo cancellation (`echoCancellation: true`, `noiseSuppression: true`).
- **Barge-in (interruption):** When the household starts speaking (or taps mute/interrupt), flush queued playback buffers immediately so the agent never talks over the caller.

## 3. Video Upgrade & Framing Hints
- When server sends `{"type":"video_link","url":"...","expires_at":"..."}`, present a clear "Switching to video" transition.
- On `/v/<token>`, request camera permission calmly, connect with `resume_conversation_id`, and send `{"type":"client_state","modality":"video","muted":false}`.
- **Frame throttling:** Send `video_frame` (`image/jpeg`, base64) at **<= 1 fps**, max **640 px** long edge. On slow connections, degrade cleanly to manual stills (`type: "image"`).
- Render `ui_hint` (`show_sticker`, `show_display`, `show_drain_filter`, `hold_steady`) as an accessible high-contrast camera framing overlay with live captions and a prominent "Stop video" button.

## 4. Resilience & Degraded States
- **`go_away`:** Show a subtle "Refreshing connection..." status; Part A rotates the Live API session transparently.
- **Socket drop:** Exponential backoff reconnect with `resume_conversation_id`; if unrecoverable, surface a calm degraded state with retry and fallback to WhatsApp/message channel.
- **Live captions:** Render every `transcript` frame verbatim in a polite `Semantics(liveRegion: true)` region tagged with its BCP 47 `lang`.
