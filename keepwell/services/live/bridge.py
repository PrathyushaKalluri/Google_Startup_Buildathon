from __future__ import annotations

import asyncio
import base64
import json
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import WebSocket, WebSocketDisconnect

from services.common.config import settings
from services.common.crypto import mask_phone
from services.common.db import get_rls_session
from services.common.logging import conversation_id_var, get_logger
from services.common.untrusted_guard import ModelArmorGuard
from services.mcp.server import TOOL_DESCRIPTIONS, invoke_mcp_tool
from services.worker.projections import projection_store

logger = get_logger("keepwell.live")
PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "live_agent.md"

RECORDING_NOTICE_BY_LANG = {
    "en": "This call may be recorded to help your service centre.",
    "hi": "यह कॉल आपके सर्विस सेंटर की मदद के लिए रिकॉर्ड की जा सकती है।",
    "te": "మీ సర్వీస్ సెంటర్ సహాయం కోసం ఈ కాల్ రికార్డ్ చేయబడవచ్చు.",
}

# Exact 16-tool Live subset from AGENTS.md Section 6.2 A4
LIVE_TOOL_SUBSET = [
    "identify_household",
    "lookup_appliance",
    "check_authority",
    "assess_urgency",
    "record_gate",
    "get_safe_fix",
    "start_fix_attempt",
    "record_fix_step",
    "record_fix_result",
    "search_manuals",
    "send_video_link",
    "flag_safety",
    "run_diagnosis",
    "build_visit_plan",
    "score_and_assign",
    "propose_slots",
]


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
    stage: str = "opened"


ACTIVE_LIVE_SESSIONS: Dict[str, LiveSessionState] = {}
RECORDED_REPLAYS: Dict[str, List[Dict[str, Any]]] = {}


def load_live_system_instruction(centre_name: str) -> str:
    template = PROMPT_PATH.read_text(encoding="utf-8")
    return template.replace("{centre_name}", centre_name)


def build_gemini_live_config(centre_name: str, resumption_handle: Optional[str] = None) -> Any:
    """
    Build google.genai.types.LiveConnectConfig with:
    - native AUDIO response modality
    - input & output audio transcription
    - sliding-window context compression (handles 2-min audio+video limit)
    - session resumption handle
    - 16 Live-subset MCP function declarations
    """
    from google.genai import types  # type: ignore

    declarations = [
        types.FunctionDeclaration(
            name=name,
            description=TOOL_DESCRIPTIONS.get(name, f"Keepwell tool {name}"),
        )
        for name in LIVE_TOOL_SUBSET
    ]
    return types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        system_instruction=load_live_system_instruction(centre_name),
        tools=[types.Tool(function_declarations=declarations)],
        input_audio_transcription=types.AudioTranscriptionConfig(),
        output_audio_transcription=types.AudioTranscriptionConfig(),
        context_window_compression=types.ContextWindowCompressionConfig(
            sliding_window=types.SlidingWindow()
        ),
        session_resumption=types.SessionResumptionConfig(handle=resumption_handle),
    )


class GeminiLiveUpstream:
    """
    Manages a live bidirectional Gemini Live API session via `client.aio.live.connect(...)`
    with transparent GoAway rotation, session resumption, PCM16 audio/video forwarding,
    transcription projection to Firestore, and MCP tool-call execution.
    """

    def __init__(self, state: LiveSessionState, websocket: WebSocket, genai_client: Any = None):
        self.state = state
        self.websocket = websocket
        self._client = genai_client
        self._audio_queue: asyncio.Queue[Optional[Dict[str, Any]]] = asyncio.Queue()
        self._task: Optional[asyncio.Task[None]] = None
        self._closed = False

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        if not (settings.gemini_api_key or settings.google_genai_use_vertexai):
            return None
        from google import genai  # type: ignore

        if settings.google_genai_use_vertexai:
            self._client = genai.Client(
                vertexai=True,
                project=settings.gcp_project_id,
                location=settings.gcp_region,
            )
        else:
            self._client = genai.Client(
                api_key=settings.gemini_api_key,
                http_options={"api_version": "v1alpha"},
            )
        return self._client

    def start(self) -> bool:
        if self._task is not None:
            return True
        if self._get_client() is None:
            return False
        self._task = asyncio.create_task(self._run_loop())
        return True

    async def send_pcm16(self, pcm_bytes: bytes) -> None:
        if not self._closed:
            await self._audio_queue.put({"kind": "audio", "data": pcm_bytes})

    async def send_video_jpeg(self, jpeg_bytes: bytes, mime: str = "image/jpeg") -> None:
        if not self._closed:
            await self._audio_queue.put({"kind": "video", "data": jpeg_bytes, "mime": mime})

    async def close(self) -> None:
        self._closed = True
        await self._audio_queue.put(None)
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _run_loop(self) -> None:
        from google.genai import types  # type: ignore

        client = self._get_client()
        if client is None:
            return

        while not self._closed:
            config = build_gemini_live_config(
                centre_name=self.state.centre_name,
                resumption_handle=self.state.resumption_handle,
            )
            try:
                async with client.aio.live.connect(
                    model=settings.gemini_model_live,
                    config=config,
                ) as session:
                    sender = asyncio.create_task(self._sender_loop(session, types))
                    try:
                        async for response in session.receive():
                            # 1. Capture session resumption handle
                            resump = getattr(response, "session_resumption_update", None)
                            if resump and getattr(resump, "new_handle", None):
                                self.state.resumption_handle = resump.new_handle

                            # 2. GoAway notice -> notify client and rotate transparently
                            go_away = getattr(response, "go_away", None)
                            if go_away is not None:
                                secs = int(getattr(go_away, "time_left", 30) or 30)
                                self.state.resumptions += 1
                                await self.websocket.send_json({"type": "go_away", "seconds": secs})
                                break

                            # 3. Audio output (PCM16 24kHz mono)
                            audio_data = getattr(response, "data", None)
                            if audio_data:
                                await self.websocket.send_bytes(audio_data)

                            # 4. Server content: transcriptions + interruptions
                            sc = getattr(response, "server_content", None)
                            if sc is not None:
                                in_tr = getattr(sc, "input_transcription", None)
                                if in_tr and getattr(in_tr, "text", None):
                                    clean_in = ModelArmorGuard.screen_inbound(in_tr.text, source="live_voice").sanitized_text
                                    turn = {
                                        "at": datetime.now(timezone.utc).isoformat(),
                                        "speaker": "household",
                                        "text": clean_in,
                                        "lang": self.state.language,
                                        "final": True,
                                        "kind": "speech",
                                    }
                                    self.state.turns.append(turn)
                                    projection_store.project_turn(self.state.centre_id, self.state.conversation_id, str(uuid.uuid4()), turn)
                                    await self.websocket.send_json({"type": "transcript", "speaker": "household", "text": clean_in, "final": True, "lang": self.state.language})

                                out_tr = getattr(sc, "output_transcription", None)
                                if out_tr and getattr(out_tr, "text", None):
                                    clean_out = ModelArmorGuard.screen_outbound(out_tr.text).sanitized_text
                                    turn = {
                                        "at": datetime.now(timezone.utc).isoformat(),
                                        "speaker": "agent",
                                        "text": clean_out,
                                        "lang": self.state.language,
                                        "final": True,
                                        "kind": "speech",
                                    }
                                    self.state.turns.append(turn)
                                    projection_store.project_turn(self.state.centre_id, self.state.conversation_id, str(uuid.uuid4()), turn)
                                    await self.websocket.send_json({"type": "transcript", "speaker": "agent", "text": clean_out, "final": True, "lang": self.state.language})

                            # 5. Live tool calls -> execute via MCP tool registry
                            tc = getattr(response, "tool_call", None)
                            if tc and getattr(tc, "function_calls", None):
                                fn_responses = []
                                for fc in tc.function_calls:
                                    args = dict(getattr(fc, "args", None) or {})
                                    args.setdefault("centre_id", self.state.centre_id)
                                    args.setdefault("conversation_id", self.state.conversation_id)
                                    if self.state.ticket_id:
                                        args.setdefault("ticket_id", self.state.ticket_id)
                                    try:
                                        result = invoke_mcp_tool(fc.name, args)
                                    except Exception as exc:
                                        result = {"error": str(exc)}
                                    fn_responses.append(
                                        types.FunctionResponse(id=fc.id, name=fc.name, response=result)
                                    )
                                await session.send_tool_response(function_responses=fn_responses)
                    finally:
                        sender.cancel()
                        try:
                            await sender
                        except asyncio.CancelledError:
                            pass
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.warning("gemini_live_degraded", extra={"extra_fields": {"error": str(exc)}})
                try:
                    await self.websocket.send_json({
                        "type": "error",
                        "code": "live_api_degraded",
                        "message": "Live audio model unavailable; falling back to recorded/text mode.",
                    })
                except Exception:
                    pass
                break

    async def _sender_loop(self, session: Any, types: Any) -> None:
        while not self._closed:
            item = await self._audio_queue.get()
            if item is None:
                break
            if item["kind"] == "audio":
                await session.send_realtime_input(
                    audio=types.Blob(data=item["data"], mime_type="audio/pcm;rate=16000")
                )
            elif item["kind"] == "video":
                await session.send_realtime_input(
                    video=types.Blob(data=item["data"], mime_type=item.get("mime", "image/jpeg"))
                )


async def handle_live_call_ws(
    websocket: WebSocket,
    orchestrator_fn: Any,
    centre_lookup_fn: Any,
) -> None:
    """
    WebSocket handler for WS /v1/live/call implementing Contract Section C7.
    """
    await websocket.accept()
    state: Optional[LiveSessionState] = None
    upstream: Optional[GeminiLiveUpstream] = None

    try:
        while True:
            msg = await websocket.receive()
            if msg["type"] == "websocket.disconnect":
                break

            # Binary PCM16 16kHz microphone audio chunk -> forward to Gemini Live API
            if msg.get("bytes") is not None:
                if state is not None:
                    live_enabled = (not settings.demo_mode) or (
                        os.getenv("KEEPWELL_LIVE_UPSTREAM", "false").lower() in ("1", "true", "yes")
                    )
                    if live_enabled:
                        if upstream is None:
                            upstream = GeminiLiveUpstream(state, websocket)
                            upstream.start()
                        await upstream.send_pcm16(msg["bytes"])
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
                b64_data = frame.get("data")
                if upstream is not None and b64_data:
                    try:
                        await upstream.send_video_jpeg(
                            base64.b64decode(b64_data),
                            mime=frame.get("mime", "image/jpeg"),
                        )
                    except Exception:
                        pass
                await websocket.send_json({
                    "type": "ui_hint",
                    "kind": "hold_steady",
                    "text": f"Captured {caption}; reading display and model details.",
                })

            elif ftype == "simulate_go_away" and state is not None and settings.demo_mode:
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

                turn_id = str(uuid.uuid4())
                now_iso = datetime.now(timezone.utc).isoformat()
                turn = {"at": now_iso, "speaker": "household", "text": utterance, "lang": state.language, "final": True, "kind": "speech"}
                state.turns.append(turn)
                projection_store.project_turn(state.centre_id, state.conversation_id, turn_id, turn)
                await websocket.send_json({"type": "transcript", "speaker": "household", "text": utterance, "final": True, "lang": state.language})

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
    finally:
        if upstream is not None:
            await upstream.close()
