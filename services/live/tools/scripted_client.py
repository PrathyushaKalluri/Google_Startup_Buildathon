"""Scripted Live Call Client for C03 Stage Scenario (Contract C7 & C8).

Connects to `WS /v1/live/call` via FastAPI `TestClient.websocket_connect`,
plays the full C03 Hindi washing-machine E21 call including Gate 1, Gate 2,
video switch, video frame, GoAway transparent rotation, failed drain-filter fix,
re-run diagnosis, visit plan, assignment, and quote, and asserts all key
Section 8 events appear in order.
"""
from __future__ import annotations

import base64
from typing import Any, Dict, List

from fastapi.testclient import TestClient

from services.api.main import app


def _drain_until(ws: Any, stop_types: set[str], max_frames: int = 30) -> List[Dict[str, Any]]:
    frames: List[Dict[str, Any]] = []
    for _ in range(max_frames):
        msg = ws.receive_json()
        frames.append(msg)
        if msg.get("type") in stop_types:
            break
    return frames


def run_c03_scripted_live_call(client: TestClient | None = None) -> Dict[str, Any]:
    """Execute scripted C03 Live WebSocket run and assert Section 7 & 8 invariants."""
    tc = client or TestClient(app)
    all_frames: List[Dict[str, Any]] = []
    event_types: List[str] = []

    def _record(frames: List[Dict[str, Any]]) -> None:
        all_frames.extend(frames)
        for f in frames:
            if f.get("type") == "event":
                # Event payload is merged at top level; handle 'type' collision gracefully
                # bridge.py sends {"type": "event", **ev}, where ev also has "type" -> ev["type"] overwrites "event"!
                pass
            if "centre_id" in f and "actor" in f and "title" in f:
                event_types.append(f["type"])

    with tc.websocket_connect("/v1/live/call?token=demo:console.c_fw@keepwell.demo") as ws:
        # 1. Start call
        ws.send_json(
            {
                "type": "start",
                "centre_key": "c_fw",
                "caller_number": "+91 50971 16577",
                "language_hint": "hi",
                "resume_conversation_id": None,
            }
        )
        # Expect ready + conversation_started + recording_notice_logged
        f1 = [ws.receive_json(), ws.receive_json(), ws.receive_json()]
        _record(f1)
        assert f1[0]["type"] == "ready", f"Expected ready frame, got {f1[0]}"
        conversation_id = f1[0]["conversation_id"]

        # 2. Send a binary PCM16 chunk (should be accepted silently)
        ws.send_bytes(b"\x00\x00" * 320)

        # 3. Household Hindi complaint (C03: Wavecrest washer E21)
        ws.send_json(
            {
                "type": "text_in",
                "text": "मेरी Wavecrest वॉशिंग मशीन में पानी नहीं निकल रहा और डिस्प्ले पर E21 आ रहा है",
            }
        )
        f2 = _drain_until(ws, {"transcript"}, max_frames=10)
        # First transcript is household, drain until agent transcript
        if f2[-1].get("speaker") == "household":
            f2.extend(_drain_until(ws, {"transcript"}, max_frames=10))
        _record(f2)

        # 4. Gate 1 -> Yes
        ws.send_json({"type": "text_in", "text": "हां, ठीक है, कोशिश करते हैं"})
        f3 = _drain_until(ws, {"transcript"}, max_frames=10)
        if f3[-1].get("speaker") == "household":
            f3.extend(_drain_until(ws, {"transcript"}, max_frames=10))
        _record(f3)

        # 5. Gate 2 -> Switch to video
        ws.send_json({"type": "text_in", "text": "हां, वीडियो पर बात करते हैं"})
        f4 = _drain_until(ws, {"transcript"}, max_frames=10)
        if f4[-1].get("speaker") == "household":
            f4.extend(_drain_until(ws, {"transcript"}, max_frames=10))
        _record(f4)
        assert any(f.get("type") == "video_link" for f in f4), "Expected video_link frame after Gate 2 video choice"

        # 6. Client switches modality to video
        ws.send_json({"type": "client_state", "modality": "video", "muted": False})
        f5 = _drain_until(ws, {"ui_hint"}, max_frames=6)
        _record(f5)
        assert any(f.get("type") == "modality" and f.get("value") == "video" for f in f5)

        # 7. Send a video frame
        ws.send_json(
            {
                "type": "video_frame",
                "mime": "image/jpeg",
                "data": base64.b64encode(b"fake-jpeg-frame").decode("ascii"),
                "ts": 1234,
                "caption": "drain_filter",
            }
        )
        f6 = [ws.receive_json()]
        _record(f6)
        assert f6[0]["type"] == "ui_hint" and f6[0]["kind"] == "hold_steady"

        # 8. Simulate GoAway rotation & transparent session resumption
        ws.send_json({"type": "simulate_go_away", "seconds": 30})
        f7 = [ws.receive_json(), ws.receive_json()]
        _record(f7)
        assert f7[0]["type"] == "go_away" and f7[0]["seconds"] == 30
        assert f7[1]["type"] == "ready" and f7[1]["conversation_id"] == conversation_id

        # 9. Household reports safe fix did not work -> re-run diagnosis -> visit plan -> assign -> quote
        ws.send_json(
            {
                "type": "text_in",
                "text": "मैंने फ़िल्टर साफ़ किया लेकिन पानी अभी भी नहीं निकल रहा और E21 आ रहा है",
            }
        )
        f8 = _drain_until(ws, {"transcript"}, max_frames=30)
        if f8[-1].get("speaker") == "household":
            f8.extend(_drain_until(ws, {"transcript"}, max_frames=30))
        _record(f8)

        # 10. End call
        ws.send_json({"type": "end", "reason": "completed"})
        f9 = [ws.receive_json()]
        _record(f9)
        assert f9[0]["type"] == "ended"
        ticket_id = f9[0].get("ticket_id")
        assert ticket_id, "Expected ticket_id in ended frame"

    # Assert key Section 8 events appeared in order
    expected_sequence = [
        "conversation_started",
        "recording_notice_logged",
        "gate_asked",
        "modality_changed",
        "household_identified",
        "appliance_identified",
        "authority_checked",
        "urgency_assessed",
        "fix_offered",
        "fix_step",
        "fix_result",
        "diagnosis_updated",
        "visit_plan_ready",
        "candidates_scored",
        "slots_offered",
        "technician_assigned",
        "quote_issued",
    ]
    cursor = 0
    for expected in expected_sequence:
        try:
            idx = event_types.index(expected, cursor)
        except ValueError as exc:
            raise AssertionError(
                f"Expected event '{expected}' after index {cursor}; got sequence: {event_types}"
            ) from exc
        cursor = idx + 1

    return {
        "conversation_id": conversation_id,
        "ticket_id": ticket_id,
        "event_types": event_types,
        "frames_count": len(all_frames),
    }


if __name__ == "__main__":
    result = run_c03_scripted_live_call()
    print(f"C03 scripted Live WS passed: ticket_id={result['ticket_id']}, events={len(result['event_types'])}")
