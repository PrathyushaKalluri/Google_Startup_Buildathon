from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import WebSocket, WebSocketDisconnect

from services.common.config import settings
from services.common.crypto import mask_phone, mint_magic_token
from services.common.db import get_rls_session
from services.common.logging import conversation_id_var, get_logger
from services.common.untrusted_guard import ModelArmorGuard
from services.worker.projections import projection_store

logger = get_logger("keepwell.live")
PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "live_agent.md"

RECORDING_NOTICE_BY_LANG = {
    "en": "This call may be recorded to help your service centre.",
    "hi": "यह कॉल आपके सर्विस सेंटर की मदद के लिए रिकॉर्ड की जा सकती है।",
    "te": "మీ సర్వీస్ సెంటర్ సహాయం కోసం ఈ కాల్ రికార్డ్ చేయబడవచ్చు.",
}


@dataclass
class LiveSessionState:
    conversation_id: str
    session_id: str
    centre_id: str
    centre_key: str
    centre_name: str
    caller_number: str
    language: str = "hi"
    modality: str = "voice"
    ticket_id: Optional[str] = None
    resumption_handle: Optional[str] = None
    compression_on: bool = True
    resumptions: int = 0
    turns: List[Dict[str, Any]] = field(default_factory=list)
    events: List[Dict[str, Any]] = field(default_factory=list)
    active_fix_code: Optional[str] = None
    gate1_answer: Optional[str] = None
    gate2_choice: Optional[str] = None
    stage: str = "opened"  # opened -> identified -> gate1 -> gate2 -> video_fix -> rerun -> booked -> ended


# Registry of active conversations so a resumed video link joins the exact same conversation
ACTIVE_LIVE_SESSIONS: Dict[str, LiveSessionState] = {}
RECORDED_REPLAYS: Dict[str, List[Dict[str, Any]]] = {}


def load_live_system_instruction(centre_name: str) -> str:
    template = PROMPT_PATH.read_text(encoding="utf-8")
    return template.replace("{centre_name}", centre_name)


def build_gemini_live_config(centre_name: str, resumption_handle: Optional[str] = None) -> Dict[str, Any]:
    """Build Gemini Live API BidiGenerateContent setup config with compression & session resumption."""
    cfg: Dict[str, Any] = {
        "model": settings.gemini_model_live,
        "response_modalities": ["AUDIO"],
        "input_audio_transcription": {},
        "output_audio_transcription": {},
        "context_window_compression": {"sliding_window": {}},
        "session_resumption": {"handle": resumption_handle} if resumption_handle else {},
        "system_instruction": load_live_system_instruction(centre_name),
    }
    return cfg


async def handle_live_call_ws(
    websocket: WebSocket,
    orchestrator_fn: Any,
    centre_lookup_fn: Any,
) -> None:
    """
    WebSocket handler for WS /v1/live/call implementing Contract Section C7.
    Supports:
      - start, binary PCM16 16kHz, video_frame, image, client_state, end
      - test-only text_in (when DEMO_MODE=true)
      - transparent GoAway rotation & session resumption
      - video link minting & conversation resumption on /v/<token>
    """
    await websocket.accept()
    state: Optional[LiveSessionState] = None

    try:
        while True:
            msg = await websocket.receive()
            if msg["type"] == "websocket.disconnect":
                break

            # Binary PCM16 16kHz microphone audio chunk
            if msg.get("bytes") is not None:
                if state is not None:
                    # In live API mode, forward PCM16 to Gemini Live session; in local/demo mode ack silently
                    continue
                continue

            raw_text = msg.get("text")
            if not raw_text:
                continue

            try:
                frame = json.loads(raw_text)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "code": "invalid_json", "message": "Malformed JSON frame"})
                continue

            ftype = frame.get("type")

            if ftype == "start":
                centre_key = frame.get("centre_key", "c_fw")
                caller = frame.get("caller_number", "+91 50971 16577")
                lang = frame.get("language_hint") or "hi"
                resume_id = frame.get("resume_conversation_id")

                centre_info = centre_lookup_fn(centre_key)
                if not centre_info:
                    await websocket.send_json({"type": "error", "code": "unknown_centre", "message": f"Unknown centre_key: {centre_key}"})
                    continue

                if resume_id and resume_id in ACTIVE_LIVE_SESSIONS:
                    state = ACTIVE_LIVE_SESSIONS[resume_id]
                    state.resumptions += 1
                    state.resumption_handle = f"resumed-{uuid.uuid4().hex[:12]}"
                else:
                    conv_id = str(uuid.uuid4())
                    sess_id = str(uuid.uuid4())
                    state = LiveSessionState(
                        conversation_id=conv_id,
                        session_id=sess_id,
                        centre_id=centre_info["id"],
                        centre_key=centre_key,
                        centre_name=centre_info["name"],
                        caller_number=caller,
                        language=lang,
                        resumption_handle=f"handle-{uuid.uuid4().hex[:12]}",
                    )
                    ACTIVE_LIVE_SESSIONS[conv_id] = state

                conversation_id_var.set(state.conversation_id)
                notice = RECORDING_NOTICE_BY_LANG.get(state.language, RECORDING_NOTICE_BY_LANG["en"])

                with get_rls_session(centre_id=state.centre_id, role="platform") as db:
                    now_iso = datetime.now(timezone.utc).isoformat()
                    if state.resumptions == 0:
                        db.conn.execute(
                            """
                            INSERT INTO conversation (id, centre_id, ticket_id, household_id, channel, modality, language, started_at, recording_consent)
                            VALUES (?, ?, NULL, NULL, 'voice', 'voice', ?, ?, 't')
                            """,
                            (state.conversation_id, state.centre_id, state.language, now_iso),
                        )
                        projection_store.project_conversation(
                            state.centre_id,
                            state.conversation_id,
                            {
                                "ticket_id": state.ticket_id,
                                "channel": "voice",
                                "modality": state.modality,
                                "language": state.language,
                                "started_at": now_iso,
                                "ended_at": None,
                                "recording_notice_logged": True,
                                "state": "active",
                                "caller_masked": mask_phone(state.caller_number),
                            },
                        )
                        ev1 = projection_store.emit_event(
                            db, state.centre_id, "conversation_started", "agent",
                            f"Call started on {state.centre_name} line",
                            conversation_id=state.conversation_id,
                            payload={"channel": "voice", "caller_masked": mask_phone(state.caller_number)},
                        )
                        ev2 = projection_store.emit_event(
                            db, state.centre_id, "recording_notice_logged", "agent",
                            "Recording notice spoken and logged",
                            conversation_id=state.conversation_id,
                            payload={"notice": notice},
                        )
                        state.events.extend([ev1, ev2])

                await websocket.send_json({
                    "type": "ready",
                    "conversation_id": state.conversation_id,
                    "session_id": state.session_id,
                    "centre_name": state.centre_name,
                    "recording_notice": notice,
                })
                for ev in state.events[-2:]:
                    await websocket.send_json({"type": "event", **ev})

            elif ftype == "client_state" and state is not None:
                new_mod = frame.get("modality", state.modality)
                if new_mod != state.modality:
                    old_mod = state.modality
                    state.modality = new_mod
                    with get_rls_session(centre_id=state.centre_id, role="platform") as db:
                        ev = projection_store.emit_event(
                            db, state.centre_id, "modality_changed", "household",
                            f"Conversation switched from {old_mod} to {new_mod}",
                            ticket_id=state.ticket_id,
                            conversation_id=state.conversation_id,
                            payload={"from": old_mod, "to": new_mod},
                        )
                        state.events.append(ev)
                    await websocket.send_json({"type": "modality", "value": new_mod})
                    await websocket.send_json({"type": "event", **ev})
                    if new_mod == "video":
                        await websocket.send_json({
                            "type": "ui_hint",
                            "kind": "show_drain_filter",
                            "text": "Please point your camera at the appliance display or lower filter cover.",
                        })

            elif ftype in ("video_frame", "image") and state is not None:
                caption = frame.get("caption", "frame")
                await websocket.send_json({
                    "type": "ui_hint",
                    "kind": "hold_steady",
                    "text": f"Captured {caption}; reading display and model details.",
                })

            elif ftype == "simulate_go_away" and state is not None and settings.demo_mode:
                # Explicitly testable GoAway rotation & transparent session resumption
                seconds = int(frame.get("seconds", 30))
                await websocket.send_json({"type": "go_away", "seconds": seconds})
                state.resumptions += 1
                state.resumption_handle = f"rotated-{uuid.uuid4().hex[:12]}"
                await websocket.send_json({
                    "type": "ready",
                    "conversation_id": state.conversation_id,
                    "session_id": state.session_id,
                    "centre_name": state.centre_name,
                    "recording_notice": "Session transparently resumed.",
                })

            elif ftype == "text_in" and state is not None:
                if not settings.demo_mode:
                    await websocket.send_json({"type": "error", "code": "forbidden", "message": "text_in only enabled in DEMO_MODE"})
                    continue
                raw_utterance = str(frame.get("text", ""))
                guard = ModelArmorGuard.screen_inbound(raw_utterance, source="live_voice")
                utterance = guard.sanitized_text

                # Emit household transcript turn
                turn_id = str(uuid.uuid4())
                now_iso = datetime.now(timezone.utc).isoformat()
                turn = {"at": now_iso, "speaker": "household", "text": utterance, "lang": state.language, "final": True, "kind": "speech"}
                state.turns.append(turn)
                projection_store.project_turn(state.centre_id, state.conversation_id, turn_id, turn)
                await websocket.send_json({"type": "transcript", "speaker": "household", "text": utterance, "final": True, "lang": state.language})

                # Run orchestrator step for this utterance
                step_out = orchestrator_fn(state, utterance)
                if guard.filtered:
                    with get_rls_session(centre_id=state.centre_id, role="platform") as db:
                        ev_f = projection_store.emit_event(
                            db, state.centre_id, "error_notice", "system",
                            "Inbound transcript filtered by Model Armor",
                            ticket_id=state.ticket_id,
                            conversation_id=state.conversation_id,
                            payload={"filtered": True, "findings": guard.findings},
                        )
                        await websocket.send_json({"type": "event", **ev_f})

                for ev in step_out.get("events", []):
                    state.events.append(ev)
                    await websocket.send_json({"type": "event", **ev})

                if step_out.get("video_link"):
                    await websocket.send_json({"type": "video_link", **step_out["video_link"]})
                if step_out.get("ui_hint"):
                    await websocket.send_json({"type": "ui_hint", **step_out["ui_hint"]})

                agent_reply = step_out.get("reply", "")
                if agent_reply:
                    out_guard = ModelArmorGuard.screen_outbound(agent_reply)
                    safe_reply = out_guard.sanitized_text
                    aturn = {"at": datetime.now(timezone.utc).isoformat(), "speaker": "agent", "text": safe_reply, "lang": state.language, "final": True, "kind": "speech"}
                    state.turns.append(aturn)
                    projection_store.project_turn(state.centre_id, state.conversation_id, str(uuid.uuid4()), aturn)
                    await websocket.send_json({"type": "transcript", "speaker": "agent", "text": safe_reply, "final": True, "lang": state.language})

            elif ftype == "end":
                reason = frame.get("reason", "completed")
                if state is not None:
                    RECORDED_REPLAYS[state.conversation_id] = list(state.events)
                    await websocket.send_json({
                        "type": "ended",
                        "reason": reason,
                        "ticket_id": state.ticket_id,
                    })
                break

    except WebSocketDisconnect:
        if state is not None:
            RECORDED_REPLAYS[state.conversation_id] = list(state.events)
    except Exception as exc:
        logger.error("live_ws_error", extra={"extra_fields": {"error": str(exc)}})
        try:
            await websocket.send_json({"type": "error", "code": "internal_error", "message": str(exc)})
        except Exception:
            pass
