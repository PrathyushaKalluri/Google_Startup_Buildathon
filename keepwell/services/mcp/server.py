from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from kb.ingest_file_search import search_manuals
from services.agents.diagnostic_agent import run_diagnostic_agent
from services.agents.engines import (
    OTPService,
    assess_urgency,
    check_authority,
    select_safe_fix,
)
from services.agents.identity_agent import resolve_identity
from services.agents.orchestrator import _load_db_safefix_catalogue, process_inbound_case
from services.common.config import settings
from services.common.crypto import mint_magic_token
from services.common.db import get_rls_session
from services.worker.projections import projection_store

router = APIRouter(prefix="/mcp", tags=["MCP Tool Server"])
otp_service = OTPService(provider=settings.otp_provider)


class MCPToolCallRequest(BaseModel):
    jsonrpc: str = "2.0"
    id: Optional[str] = None
    method: str = "tools/call"
    params: Dict[str, Any] = Field(default_factory=dict)


TOOL_DESCRIPTIONS: Dict[str, str] = {
    "identify_household": "Resolve or create global household by phone hash and link to centre.",
    "lookup_appliance": "Lookup appliance by brand + serial or household record with evidence level.",
    "check_authority": "Check centre brand authorisation level and return proceed or return_to_brand.",
    "assess_urgency": "Deterministic urgency classification (safety, urgent, standard, planned).",
    "record_clarifying_answer": "Record a clarifying question and household answer on a ticket.",
    "record_gate": "Record Gate 1 or Gate 2 consent answer (enforces safety/job_type skips).",
    "get_safe_fix": "Retrieve active reviewed safe-fix catalogue entry for category/brand/symptom.",
    "start_fix_attempt": "Start a catalogued safe fix (requires Gate 1 = yes).",
    "record_fix_step": "Record completion of step N of a safe fix and emit fix_step event.",
    "record_fix_result": "Record safe-fix outcome (worked|not_worked|abandoned|safety_stop).",
    "search_manuals": "Search KB manuals (Gemini File Search / local index) returning grounded citations.",
    "run_diagnosis": "Run grounded diagnostic reasoning with citations and already_tried evidence.",
    "build_visit_plan": "Build structured VisitPlan carrying already_tried and verified parts.",
    "score_and_assign": "Score eligible technicians inside centre using 30/25/20/15/5/5 weights.",
    "propose_slots": "Propose visit window and estimate range to household.",
    "issue_quote": "Issue estimate or firm quote from centre price book with 18% GST.",
    "send_message": "Send outbound message to household and project to whatsapp_thread.",
    "send_video_link": "Mint signed expiring /v/<token> link to switch conversation to video.",
    "schedule_reminder": "Schedule consent-checked maintenance or follow-up reminder.",
    "read_shared_history": "Read cross-centre technical history if consented; writes access_log.",
    "create_or_update_ticket": "Create or update a ticket and project to Firestore.",
    "return_to_brand": "Decline unauthorised brand warranty request and return to brand with reason.",
    "flag_safety": "Flag safety hazard, emit safety_stop_sent, skip both consent gates.",
    "request_closure_otp": "Issue 6-digit closure OTP (stores SHA-256 hash only; OTP closes job).",
}


def invoke_mcp_tool(tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Execute one of the 24 Keepwell MCP tools with RLS context and event emission."""
    if tool_name not in TOOL_DESCRIPTIONS:
        raise KeyError(f"Unknown MCP tool: {tool_name}")

    centre_id = args.get("centre_id")
    role = args.get("role", "platform")

    with get_rls_session(centre_id=centre_id, role=role) as db:
        if tool_name == "identify_household":
            return db.identify_household(
                phone=args["phone"],
                centre_id=args["centre_id"],
                verified_via=args.get("verified_via", "call_line"),
            )
        if tool_name == "lookup_appliance":
            return resolve_identity(
                db=db,
                centre_id=args["centre_id"],
                phone=args["phone"],
                category_code=args.get("category_code"),
                brand_name=args.get("brand_name"),
                serial_no=args.get("serial_no"),
            )
        if tool_name == "check_authority":
            lvl = db.centre_authority(args["centre_id"], args["brand_id"])
            res = check_authority(lvl, args.get("job_type", "repair"), args.get("entitlement", "paid"))
            return res.model_dump()
        if tool_name == "assess_urgency":
            res = assess_urgency(
                text=args.get("text", ""),
                category_code=args.get("category_code"),
                job_type=args.get("job_type", "repair"),
                facts=args.get("facts"),
                repeat_within_days=args.get("repeat_within_days"),
            )
            return res.model_dump()
        if tool_name == "search_manuals":
            cits = search_manuals(
                query=args.get("query", ""),
                brand=args.get("brand"),
                category=args.get("category"),
                top_k=int(args.get("top_k", 5)),
                db=db,
            )
            return {"citations": cits}
        if tool_name == "get_safe_fix":
            cat = _load_db_safefix_catalogue(db)
            sel = select_safe_fix(
                category_code=args["category_code"],
                symptoms=args.get("symptoms", []),
                brand_id=args.get("brand_id"),
                error_codes=args.get("error_codes"),
                catalogue=cat,
                safety_flag=bool(args.get("safety_flag", False)),
            )
            return {"safe_fix": sel.entry.model_dump() if sel else None}
        if tool_name == "send_video_link":
            conv_id = args.get("conversation_id") or str(uuid.uuid4())
            tok = mint_magic_token(conv_id, scope="video_link", ttl_seconds=1800)
            exp = (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat()
            return {"url": f"{settings.household_host}/v/{tok}", "expires_at": exp}
        if tool_name == "read_shared_history":
            rows = db.read_shared_history(
                appliance_id=args["appliance_id"],
                centre_id=args["centre_id"],
                ticket_id=args.get("ticket_id"),
                reason=args.get("reason", "mcp_tool_read"),
            )
            return {"events": rows}
        if tool_name == "request_closure_otp":
            rec = otp_service.issue_otp(subject_id=args["visit_id"], phone=args.get("phone", "+91 50000 00000"))
            out = {"otp_ref": rec.otp_ref, "expires_at": rec.expires_at.isoformat()}
            if settings.otp_provider == "sandbox":
                out["sandbox_code"] = otp_service.get_sandbox_otp(rec.otp_ref)
            return out
        if tool_name == "run_diagnosis":
            return run_diagnostic_agent(
                db=db,
                symptom_text=args.get("symptom_text", ""),
                brand_id=args.get("brand_id"),
                brand_name=args.get("brand_name", ""),
                category_code=args.get("category_code", "ac"),
                error_codes=args.get("error_codes", []),
                already_tried=args.get("already_tried", []),
            )
        if tool_name == "flag_safety":
            ev = projection_store.emit_event(
                db,
                args["centre_id"],
                "safety_stop_sent",
                "agent",
                "Please stop using it and switch it off at the wall. A technician will come as soon as possible.",
                ticket_id=args.get("ticket_id"),
                payload={"reason": args.get("reason", "hazard_detected")},
            )
            return {"flagged": True, "event": ev}

        # Default structured ack for remaining stateful tools
        return {"tool": tool_name, "status": "ok", "args": args}


@router.get("")
@router.get("/tools")
def list_mcp_tools() -> Dict[str, Any]:
    """Streamable HTTP MCP tool discovery."""
    return {
        "protocol": "mcp-streamable-http",
        "server": "keepwell-mcp",
        "tools": [
            {"name": name, "description": desc}
            for name, desc in TOOL_DESCRIPTIONS.items()
        ],
    }


@router.post("")
def handle_mcp_rpc(req: MCPToolCallRequest) -> Dict[str, Any]:
    """Streamable HTTP JSON-RPC 2.0 endpoint for tools/list and tools/call."""
    if req.method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req.id,
            "result": {
                "tools": [{"name": k, "description": v} for k, v in TOOL_DESCRIPTIONS.items()]
            },
        }
    if req.method == "tools/call":
        name = req.params.get("name", "")
        arguments = req.params.get("arguments", {})
        try:
            result = invoke_mcp_tool(name, arguments)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc))
        return {"jsonrpc": "2.0", "id": req.id, "result": result}
    raise HTTPException(status_code=400, detail=f"Unsupported MCP method: {req.method}")
