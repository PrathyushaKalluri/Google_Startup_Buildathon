"""Keepwell Part B Mock Live Call WebSocket Server (Contract Section 7).

Runs on port 8082 (`uvicorn mocks.ws.server:app --port 8082`), path `/v1/live/call`.
Supports:
- Default C03 replay mode: streams realistic C03 Hindi/English transcripts, synthetic
  PCM16 24kHz audio chunks, video_link, modality switch, ui_hints, Section 8 events,
  go_away, and ended.
- Echo mode (`language_hint == "echo"`): echoes back client messages for standalone dialer testing.
"""

from __future__ import annotations

import asyncio
import json
import math
import os
import struct
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from mocks.fixtures.build_fixtures import OUT_DIR as FIXTURES_DIR, build_all

IST = timezone(timedelta(hours=5, minutes=30))


def now_iso() -> str:
    return datetime.now(IST).isoformat(timespec="seconds")


def load_c03_script() -> dict[str, Any]:
    path = FIXTURES_DIR / "c03_script.json"
    if not path.exists():
        build_all()
    return json.loads(path.read_text(encoding="utf-8"))


def synth_pcm16_24khz(duration_ms: int = 80, freq_hz: float = 440.0) -> bytes:
    """Generate a short, gentle PCM16 little-endian 24kHz mono tone burst."""
    sample_rate = 24000
    n_samples = int(sample_rate * duration_ms / 1000)
    samples = []
    for i in range(n_samples):
        val = int(2800 * math.sin(2.0 * math.pi * freq_hz * i / sample_rate))
        samples.append(val)
    return struct.pack(f"<{n_samples}h", *samples)


def make_event(
    centre_id: str,
    ticket_id: str,
    conversation_id: str,
    ev_type: str,
    actor: str,
    title: str,
    detail: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "type": "event",
        "id": str(uuid.uuid4()),
        "at": now_iso(),
        "centre_id": centre_id,
        "ticket_id": ticket_id,
        "conversation_id": conversation_id,
        "event_type": ev_type,
        "actor": actor,
        "title": title,
        "detail": detail,
        "payload": payload or {},
    }


app = FastAPI(title="Keepwell Mock Live WS Server", version="0.1.0-mock")


@app.get("/healthz")
def healthz():
    return {"status": "ok", "service": "keepwell-mock-ws"}


@app.websocket("/v1/live/call")
async def live_call_ws(websocket: WebSocket):
    await websocket.accept()
    step_delay = float(os.getenv("MOCK_WS_DELAY_S", "0.12"))
    script = load_c03_script()

    try:
        # Wait for initial start frame
        first_msg = await websocket.receive_text()
        start = json.loads(first_msg)
    except WebSocketDisconnect:
        return
    except Exception:
        await websocket.send_json({"type": "error", "code": "invalid_start", "message": "Expected JSON start frame"})
        await websocket.close()
        return

    conv_id = start.get("resume_conversation_id") or str(uuid.uuid4())
    session_id = f"sess_{uuid.uuid4().hex[:10]}"
    language_hint = start.get("language_hint")
    centre_name = script["centre_name"]
    recording_notice = "This call may be recorded to help your service centre."

    await websocket.send_json({
        "type": "ready",
        "conversation_id": conv_id,
        "session_id": session_id,
        "centre_name": centre_name,
        "recording_notice": recording_notice,
    })

    # --- Mode 2: Echo Mode ---
    if language_hint == "echo":
        try:
            while True:
                msg = await websocket.receive()
                if msg.get("type") == "websocket.disconnect":
                    break
                if msg.get("bytes") is not None:
                    # Echo back a tiny synthetic PCM16 24kHz reply
                    await websocket.send_bytes(synth_pcm16_24khz(40, 520.0))
                elif msg.get("text") is not None:
                    data = json.loads(msg["text"])
                    mtype = data.get("type")
                    if mtype == "end":
                        await websocket.send_json({
                            "type": "ended",
                            "reason": "completed",
                            "ticket_id": script["ticket_id"],
                        })
                        break
                    elif mtype == "client_state" and data.get("modality") == "video":
                        await websocket.send_json({"type": "modality", "value": "video"})
                        await websocket.send_json({
                            "type": "ui_hint",
                            "kind": "hold_steady",
                            "text": "Echo mode: camera stream active — hold steady.",
                        })
                    else:
                        await websocket.send_json({
                            "type": "transcript",
                            "speaker": "agent",
                            "text": f"Echo: {mtype} received",
                            "final": True,
                            "lang": "en",
                        })
        except WebSocketDisconnect:
            return
        return

    # --- Mode 1: Default C03 Replay Mode ---
    cid = script["centre_id"]
    tid = script["ticket_id"]
    magic_token = script["magic_token"]

    async def poll_client_nonblocking() -> bool:
        """Process any incoming client frames (client_state, video_frame, image, end) without blocking."""
        try:
            raw = await asyncio.wait_for(websocket.receive(), timeout=step_delay)
            if raw.get("type") == "websocket.disconnect":
                return False
            if raw.get("text"):
                data = json.loads(raw["text"])
                mtype = data.get("type")
                if mtype == "end":
                    await websocket.send_json({"type": "ended", "reason": "household_left", "ticket_id": tid})
                    return False
                if mtype == "client_state" and data.get("modality") == "video":
                    await websocket.send_json({"type": "modality", "value": "video"})
                    await websocket.send_json(
                        make_event(
                            cid, tid, conv_id, "modality_changed", "household",
                            "Switched from voice to live video",
                            "Household opened video link and enabled camera",
                            {"from": "voice", "to": "video"},
                        )
                    )
                elif mtype in ("video_frame", "image"):
                    await websocket.send_json({
                        "type": "ui_hint",
                        "kind": "hold_steady",
                        "text": "Hold steady — reading display code E21.",
                    })
        except asyncio.TimeoutError:
            pass
        except WebSocketDisconnect:
            return False
        return True

    steps: list[tuple[str, Any]] = [
        ("json", make_event(cid, tid, conv_id, "conversation_started", "household", "Inbound Hindi voice call to Frost and Wave Service Point", script["caller_number"], {"channel": "voice", "caller_masked": "+91 ••••• ••577"})),
        ("json", make_event(cid, tid, conv_id, "recording_notice_logged", "system", "Recording notice played", recording_notice, {})),
        ("json", {"type": "transcript", "speaker": "household", "text": script["opening_hi"], "final": True, "lang": "hi"}),
        ("bytes", synth_pcm16_24khz(60, 440.0)),
        ("json", make_event(cid, tid, conv_id, "household_identified", "agent", f"Identified {script['household_name']}", "Matched via call_line", {"household_id": script["household_id"], "verified_via": "call_line", "known_to_this_centre": True})),
        ("json", make_event(cid, tid, conv_id, "appliance_identified", "agent", "Wavecrest Front-Load Washer identified", "Warranty ended 22 days ago", {"brand": "Wavecrest", "source": "record"})),
        ("json", make_event(cid, tid, conv_id, "authority_checked", "agent", "Authority confirmed: authorised_service for Wavecrest", "Proceeding with triage", {"level": "authorised_service", "decision": "proceed"})),
        ("json", make_event(cid, tid, conv_id, "urgency_assessed", "agent", "Urgency assessed: standard", "No electrical/safety hazard; floor wet only", {"class": "standard", "rule_codes": ["STD-DEFAULT"]})),
        ("json", {"type": "transcript", "speaker": "agent", "text": "क्या आप पहले एक छोटा और सुरक्षित उपाय खुद आज़माना चाहेंगी? (Are you okay to try a quick, safe fix yourself first?)", "final": True, "lang": "hi"}),
        ("json", make_event(cid, tid, conv_id, "gate_asked", "agent", "Consent Gate 1 asked", "Safe self-fix permission", {"gate": 1})),
        ("json", {"type": "transcript", "speaker": "household", "text": "जी हाँ, अगर आसान है तो ठीक है। (Yes, if it is simple.)", "final": True, "lang": "hi"}),
        ("json", make_event(cid, tid, conv_id, "gate_answered", "household", "Gate 1 answered: yes", "Household agreed to safe fix", {"gate": 1, "answer": "yes", "choice": None})),
        ("json", {"type": "transcript", "speaker": "agent", "text": "क्या आप वीडियो पर आना चाहेंगी, या यहीं कॉल पर आगे बढ़ें? (Would you like to switch to video, or carry on here?)", "final": True, "lang": "hi"}),
        ("json", make_event(cid, tid, conv_id, "gate_asked", "agent", "Consent Gate 2 asked", "Video switch offer", {"gate": 2})),
        ("json", {"type": "transcript", "speaker": "household", "text": "वीडियो लिंक भेज दीजिए। (Yes, send the video link.)", "final": True, "lang": "hi"}),
        ("json", make_event(cid, tid, conv_id, "gate_answered", "household", "Gate 2 answered: switch_to_video", "Sending magic video link", {"gate": 2, "answer": "yes", "choice": "switch_to_video"})),
        ("json", {"type": "video_link", "url": f"http://localhost:8080/v/{magic_token}", "expires_at": (datetime.now(IST) + timedelta(minutes=20)).isoformat(timespec="seconds")}),
        ("json", {"type": "modality", "value": "video"}),
        ("json", {"type": "ui_hint", "kind": "show_sticker", "text": "Point the camera at the model sticker inside the door rim."}),
        ("json", {"type": "ui_hint", "kind": "show_display", "text": "Show the E21 error code on the front display."}),
        ("json", {"type": "ui_hint", "kind": "show_drain_filter", "text": "Point at the small square drain filter cover at the bottom right."}),
        ("json", {"type": "ui_hint", "kind": "hold_steady", "text": "Hold steady while we check the drain filter cavity."}),
        ("json", make_event(cid, tid, conv_id, "fix_offered", "agent", f"Offered {script['safe_fix_code']}: {script['safe_fix_title']}", "6 reversible steps, ~10 min", {"code": script["safe_fix_code"], "steps": 6})),
        ("json", make_event(cid, tid, conv_id, "fix_step", "agent", "Completed step 6 of 6", "Coins, hair-clips and lint cleared from filter", {"n": 6, "of": 6})),
        ("bytes", synth_pcm16_24khz(60, 587.33)),
        ("json", {"type": "transcript", "speaker": "household", "text": "पानी थोड़ा निकला, लेकिन फिर से E21 आ गया। (Water drained partly, then E21 returned.)", "final": True, "lang": "hi"}),
        ("json", make_event(cid, tid, conv_id, "fix_result", "household", "Safe fix outcome: not_worked", "E21 returned after drain filter clean", {"outcome": "not_worked"})),
        ("json", make_event(cid, tid, conv_id, "diagnosis_updated", "agent", "Diagnosis re-run: drain pump impeller jammed (86%)", "Part WC-WM-DPUMP added to visit plan", {"probability": 0.86, "rerun": True})),
        ("json", make_event(cid, tid, conv_id, "visit_plan_ready", "agent", "Visit plan ready with WC-WM-DPUMP", "Already tried: SF-WM-DRAINFILTER-WC", {"already_tried": [script["safe_fix_code"]]})),
        ("json", make_event(cid, tid, conv_id, "candidates_scored", "agent", "Top 3 technicians scored (6-factor ranking)", f"#1 {script['candidates'][0]['name']} (89.5)", {"top_3": script["candidates"]})),
        ("json", make_event(cid, tid, conv_id, "slots_offered", "agent", "Offered 14:00-16:00 slot (₹1,000 - ₹2,235)", "Household accepted slot", {"window": "14:00-16:00"})),
        ("json", make_event(cid, tid, conv_id, "technician_assigned", "agent", f"Assigned {script['candidates'][0]['name']} for 14:00-16:00", "Chosen by agent", {"name": script["candidates"][0]["name"], "chosen_by": "agent"})),
        ("json", {"type": "go_away", "seconds": 30}),
        ("json", {"type": "ended", "reason": "completed", "ticket_id": tid}),
    ]

    try:
        for kind, payload in steps:
            if kind == "json":
                await websocket.send_json(payload)
            else:
                await websocket.send_bytes(payload)
            keep_going = await poll_client_nonblocking()
            if not keep_going:
                return
    except WebSocketDisconnect:
        return


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("mocks.ws.server:app", host="0.0.0.0", port=int(os.getenv("MOCK_WS_PORT", "8082")), reload=False)
