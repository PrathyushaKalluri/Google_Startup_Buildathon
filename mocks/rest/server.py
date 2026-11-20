"""Keepwell Part B Mock REST Server (Contract Section 5).

Runs on port 8081 (`uvicorn mocks.rest.server:app --port 8081`).
Loads normalized fixtures from `mocks/fixtures/generated/` (auto-building them if absent).
"""

from __future__ import annotations

import copy
import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse

from mocks.fixtures.build_fixtures import OUT_DIR as FIXTURES_DIR, build_all

IST = timezone(timedelta(hours=5, minutes=30))
URGENCY_RANK = {"safety": 0, "urgent": 1, "standard": 2, "planned": 3}


def now_iso() -> str:
    return datetime.now(IST).isoformat(timespec="seconds")


def make_error(code: str, message: str, field: str | None = None, status_code: int = 400) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "field": field,
                "request_id": f"req_{uuid.uuid4().hex[:12]}",
            }
        },
    )


def paginate(items: list[Any], cursor: str | None = None, limit: int = 50) -> dict[str, Any]:
    start = 0
    if cursor:
        try:
            start = max(0, int(cursor))
        except ValueError:
            start = 0
    page = items[start : start + limit]
    next_cursor = str(start + limit) if (start + limit) < len(items) else None
    return {"items": page, "next_cursor": next_cursor}


class MockStore:
    """In-memory mutable state initialized from `mocks/fixtures/generated/`."""

    def __init__(self) -> None:
        self.reset()

    def _load(self, name: str) -> Any:
        path = FIXTURES_DIR / name
        if not path.exists():
            build_all()
        return json.loads(path.read_text(encoding="utf-8"))

    def reset(self) -> None:
        if not (FIXTURES_DIR / "tickets.json").exists():
            build_all()
        self.centres: list[dict[str, Any]] = self._load("centres.json")
        self.centres_by_id = {c["id"]: c for c in self.centres}
        self.centres_by_key = {c["centre_key"]: c for c in self.centres}

        self.technicians: list[dict[str, Any]] = self._load("technicians.json")
        self.techs_by_id = {t["id"]: t for t in self.technicians}

        self.households: list[dict[str, Any]] = self._load("households.json")
        self.households_by_id = {h["id"]: h for h in self.households}
        self.households_by_token = {h["magic_token"]: h for h in self.households}

        self.appliances: list[dict[str, Any]] = self._load("appliances.json")
        self.appliances_by_id = {a["id"]: a for a in self.appliances}

        raw_tickets: list[dict[str, Any]] = self._load("tickets.json")
        self.tickets: dict[str, dict[str, Any]] = {}
        self.tickets_by_case: dict[str, str] = {}
        self.visits_by_id: dict[str, tuple[str, dict[str, Any]]] = {}
        for t in raw_tickets:
            tid = t["card"]["id"]
            self.tickets[tid] = t
            if t.get("case_id"):
                self.tickets_by_case[t["case_id"]] = tid
            if t.get("visit"):
                self.visits_by_id[t["visit"]["id"]] = (tid, t["visit"])

        self.safefix: list[dict[str, Any]] = self._load("safefix.json")
        self.safefix_by_code = {s["code"]: s for s in self.safefix}

        parts_data = self._load("parts.json")
        self.part_catalogue: list[dict[str, Any]] = parts_data["catalogue"]
        self.parts_centres: list[dict[str, Any]] = parts_data["parts_centres"]
        self.stock: list[dict[str, Any]] = parts_data["stock"]
        self.centre_prices: list[dict[str, Any]] = parts_data["centre_prices"]
        self.parts_requests: dict[str, dict[str, Any]] = {
            r["id"]: r for r in parts_data["parts_requests"]
        }

        self.demo_cases: list[dict[str, Any]] = self._load("demo_cases.json")
        self.demo_households: list[dict[str, Any]] = self._load("demo_households.json")
        self.brands_retailers: dict[str, Any] = self._load("brands_retailers.json")
        self.overview: dict[str, dict[str, Any]] = self._load("overview.json")
        self.whatsapp_threads: dict[str, list[dict[str, Any]]] = self._load("whatsapp_threads.json")

        self.overrides: list[dict[str, Any]] = []
        self.otp_store: dict[str, dict[str, Any]] = {}
        self.active_case_id: str | None = "C03"
        self.reset_at: str = now_iso()

    def resolve_centre_id(self, centre_id: str | None = None, centre_key: str | None = None) -> str:
        if centre_id and centre_id in self.centres_by_id:
            return centre_id
        if centre_key and centre_key in self.centres_by_key:
            return self.centres_by_key[centre_key]["id"]
        # Default to c_fw (Frost and Wave Service Point — stage demo centre)
        return self.centres_by_key["c_fw"]["id"]

    def public_ticket_detail(self, raw: dict[str, Any]) -> dict[str, Any]:
        # Return exact C5.1 TicketDetail fields (strip internal case_id helper key if needed, or keep clean)
        keys = [
            "card", "case_card", "urgency", "gates", "clarifying_qa",
            "fix_attempts", "tried_summary", "diagnosis", "visit_plan",
            "candidates", "slot_proposals", "quotes", "payments",
            "debrief", "visit", "timeline", "authority",
        ]
        return {k: copy.deepcopy(raw.get(k)) for k in keys}

    def find_ticket_for_household_token(self, token: str) -> tuple[dict[str, Any], dict[str, Any]]:
        hh = self.households_by_token.get(token)
        if not hh:
            # Also allow passing a household_id or ticket_id directly in local dev
            hh = self.households_by_id.get(token)
        if not hh:
            raise HTTPException(status_code=404, detail=("token_not_found", "Invalid or expired magic token"))
        for t in self.tickets.values():
            if t["card"]["household"]["id"] == hh["id"]:
                return hh, t
        # Fallback to C03 ticket if household has no open ticket
        c03_id = self.tickets_by_case.get("C03")
        return hh, self.tickets[c03_id] if c03_id else next(iter(self.tickets.values()))


store = MockStore()

app = FastAPI(
    title="Keepwell Mock REST API v1",
    version="0.1.0-mock",
    description="Contract-exact local mock REST server for Keepwell Part B.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def mock_fail_middleware(request: Request, call_next):
    fail_header = request.headers.get("X-Mock-Fail")
    if fail_header:
        try:
            code = int(fail_header)
        except ValueError:
            code = 500
        return make_error(
            code="mock_injected_failure",
            message=f"Simulated HTTP {code} error via X-Mock-Fail header",
            status_code=code,
        )
    return await call_next(request)


@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException):
    if isinstance(exc.detail, tuple) and len(exc.detail) == 2:
        code, msg = exc.detail
    else:
        code = f"http_{exc.status_code}"
        msg = str(exc.detail)
    return make_error(code=code, message=msg, status_code=exc.status_code)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request: Request, exc: RequestValidationError):
    first = exc.errors()[0] if exc.errors() else {}
    field = ".".join(str(x) for x in first.get("loc", [])) or None
    return make_error(
        code="validation_error",
        message=first.get("msg", "Invalid request payload"),
        field=field,
        status_code=422,
    )


# ---------------------------------------------------------------------------
# Health & Meta
# ---------------------------------------------------------------------------

@app.get("/healthz")
def healthz():
    return {"status": "ok", "service": "keepwell-mock-rest"}


@app.get("/readyz")
def readyz():
    return {"status": "ready", "tickets_loaded": len(store.tickets), "centres_loaded": len(store.centres)}


@app.get("/v1/meta/version")
def meta_version():
    return {
        "service": "keepwell-mock-rest",
        "contract_version": "v1",
        "mode": "mock",
        "payment_mode": os.getenv("PAYMENT_MODE", "sandbox"),
        "demo_mode": True,
    }


# ---------------------------------------------------------------------------
# Centre Console Endpoints
# ---------------------------------------------------------------------------

@app.get("/v1/tickets")
def list_tickets(
    status: str | None = None,
    urgency_class: str | None = None,
    trigger: str | None = None,
    q: str | None = None,
    centre_id: str | None = None,
    centre_key: str | None = None,
    cursor: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
):
    cards = [t["card"] for t in store.tickets.values()]
    if centre_key and centre_key in store.centres_by_key:
        cid = store.centres_by_key[centre_key]["id"]
        cards = [c for c in cards if c["centre_id"] == cid]
    elif centre_id:
        cards = [c for c in cards if c["centre_id"] == centre_id]
    if status:
        cards = [c for c in cards if c["status"] == status]
    if urgency_class:
        cards = [c for c in cards if c["urgency_class"] == urgency_class]
    if trigger:
        cards = [c for c in cards if c["trigger"] == trigger]
    if q:
        ql = q.lower()
        cards = [
            c
            for c in cards
            if ql in c["complaint_summary"].lower()
            or ql in c["household"]["display_name"].lower()
            or (c["appliance"] and ql in (c["appliance"]["brand"] or "").lower())
        ]

    # Contract ordering: safety, urgent, standard, planned, then needed_by
    cards.sort(key=lambda c: (URGENCY_RANK.get(c["urgency_class"], 9), c.get("needed_by") or ""))
    return paginate(cards, cursor=cursor, limit=limit)


@app.get("/v1/tickets/{ticket_id}")
def get_ticket(ticket_id: str):
    raw = store.tickets.get(ticket_id)
    if not raw and ticket_id in store.tickets_by_case:
        raw = store.tickets[store.tickets_by_case[ticket_id]]
    if not raw:
        raise HTTPException(status_code=404, detail=("ticket_not_found", f"Ticket {ticket_id} not found"))
    return store.public_ticket_detail(raw)


@app.post("/v1/tickets/{ticket_id}/reclassify-urgency")
async def reclassify_urgency(ticket_id: str, request: Request):
    raw = store.tickets.get(ticket_id)
    if not raw:
        raise HTTPException(status_code=404, detail=("ticket_not_found", f"Ticket {ticket_id} not found"))
    body = await request.json()
    new_class = body.get("class")
    reason = body.get("reason", "Centre operator override")
    if new_class not in URGENCY_RANK:
        raise HTTPException(status_code=422, detail=("invalid_urgency_class", f"Invalid class: {new_class}"))

    old_class = raw["card"]["urgency_class"]
    ts = now_iso()
    raw["card"]["urgency_class"] = new_class
    raw["card"]["safety_flag"] = new_class == "safety"
    if new_class == "safety":
        raw["card"]["safety_reason"] = reason
    raw["card"]["updated_at"] = ts
    raw["urgency"].append({
        "class": new_class,
        "rule_codes": ["CTR-OVERRIDE"],
        "facts": {"previous_class": old_class},
        "assessed_by": "centre_console",
        "reason": reason,
        "protective_steps_sent": new_class == "safety",
        "created_at": ts,
    })
    raw["timeline"].append({
        "at": ts,
        "type": "urgency_assessed",
        "actor": "centre",
        "title": f"Urgency reclassified from {old_class} to {new_class}",
        "detail": reason,
        "ref": ticket_id,
    })
    store.overrides.append({
        "id": f"ovr_{uuid.uuid4().hex[:10]}",
        "centre_id": raw["card"]["centre_id"],
        "ticket_id": ticket_id,
        "kind": "urgency_reclassification",
        "from_value": old_class,
        "to_value": new_class,
        "reason": reason,
        "at": ts,
    })
    return store.public_ticket_detail(raw)


@app.post("/v1/tickets/{ticket_id}/reassign")
async def reassign_ticket(ticket_id: str, request: Request):
    raw = store.tickets.get(ticket_id)
    if not raw:
        raise HTTPException(status_code=404, detail=("ticket_not_found", f"Ticket {ticket_id} not found"))
    body = await request.json()
    tech_id = body.get("technician_id")
    slot_start = body.get("slot_start") or "2026-11-21T16:00:00+05:30"
    slot_end = body.get("slot_end") or "2026-11-21T18:00:00+05:30"
    reason = body.get("reason", "Centre reassignment")
    tech = store.techs_by_id.get(tech_id)
    if not tech:
        raise HTTPException(status_code=404, detail=("technician_not_found", f"Technician {tech_id} not found"))

    ts = now_iso()
    old_tech_id = raw["visit"]["technician_id"] if raw.get("visit") else None
    old_tech_name = store.techs_by_id.get(old_tech_id, {}).get("name", "Unassigned") if old_tech_id else "Unassigned"

    found = False
    for c in raw["candidates"]:
        if c["technician_id"] == tech_id:
            c["outcome"] = "chosen"
            c["chosen_by"] = "centre_console"
            c["override_reason"] = reason
            c["slot_start"] = slot_start
            c["slot_end"] = slot_end
            found = True
        else:
            c["outcome"] = "not_chosen"
    if not found:
        raw["candidates"].insert(0, {
            "technician_id": tech_id,
            "name": tech["name"],
            "rank": 1,
            "score": 82.0,
            "score_breakdown": {
                "fix_confidence": 25.0,
                "parts_readiness": 21.0,
                "time_to_visit": 16.0,
                "route_cost": 11.5,
                "reliability": 4.5,
                "household_fit": 4.0,
            },
            "slot_start": slot_start,
            "slot_end": slot_end,
            "outcome": "chosen",
            "chosen_by": "centre_console",
            "override_reason": reason,
            "why": f"Manually reassigned by centre: {reason}",
        })

    if raw.get("visit"):
        raw["visit"]["technician_id"] = tech_id
        raw["visit"]["planned_start"] = slot_start
        raw["visit"]["planned_end"] = slot_end
    raw["card"]["status"] = "assigned"
    raw["card"]["updated_at"] = ts
    raw["timeline"].append({
        "at": ts,
        "type": "reassigned",
        "actor": "centre",
        "title": f"Reassigned from {old_tech_name} to {tech['name']}",
        "detail": reason,
        "ref": tech_id,
    })
    store.overrides.append({
        "id": f"ovr_{uuid.uuid4().hex[:10]}",
        "centre_id": raw["card"]["centre_id"],
        "ticket_id": ticket_id,
        "kind": "reassignment",
        "from_value": old_tech_name,
        "to_value": tech["name"],
        "reason": reason,
        "at": ts,
    })
    return store.public_ticket_detail(raw)


@app.post("/v1/tickets/{ticket_id}/rerun-diagnosis")
def rerun_diagnosis(ticket_id: str):
    raw = store.tickets.get(ticket_id)
    if not raw:
        raise HTTPException(status_code=404, detail=("ticket_not_found", f"Ticket {ticket_id} not found"))
    ts = now_iso()
    prev_diag = raw.get("diagnosis") or {}
    hyps = copy.deepcopy(prev_diag.get("hypotheses", []))
    if hyps:
        hyps[0]["probability"] = min(0.95, round(hyps[0].get("probability", 0.75) + 0.06, 2))
        hyps[0].setdefault("evidence", []).append(f"Re-run requested by centre at {ts}")
    raw["diagnosis"] = {
        "hypotheses": hyps,
        "abstained": False,
        "reason": None,
        "rerun_of": f"diag_{uuid.uuid4().hex[:8]}",
        "model_version": "gemini-3.8-flash",
    }
    if raw.get("visit_plan"):
        raw["visit_plan"]["version"] = raw["visit_plan"].get("version", 1) + 1
        raw["visit_plan"]["trigger_reason"] = "centre_rerun_diagnosis"
    raw["card"]["updated_at"] = ts
    raw["timeline"].append({
        "at": ts,
        "type": "diagnosis_updated",
        "actor": "agent",
        "title": "Diagnosis and visit plan re-run completed",
        "detail": hyps[0]["label"] if hyps else "Updated hypotheses",
        "ref": ticket_id,
    })
    return store.public_ticket_detail(raw)


@app.post("/v1/tickets/{ticket_id}/return-to-brand")
async def return_to_brand(ticket_id: str, request: Request):
    raw = store.tickets.get(ticket_id)
    if not raw:
        raise HTTPException(status_code=404, detail=("ticket_not_found", f"Ticket {ticket_id} not found"))
    body = await request.json()
    reason = body.get("reason", "Centre lacks brand warranty authorisation")
    ts = now_iso()
    raw["authority"]["decision"] = "declined"
    raw["card"]["status"] = "returned_to_brand"
    raw["card"]["resolution"] = "returned_to_brand"
    raw["card"]["updated_at"] = ts
    raw["timeline"].append({
        "at": ts,
        "type": "brand_request_declined",
        "actor": "centre",
        "title": "Ticket returned to brand",
        "detail": reason,
        "ref": ticket_id,
    })
    return store.public_ticket_detail(raw)


@app.post("/v1/tickets/{ticket_id}/message")
async def send_ticket_message(ticket_id: str, request: Request):
    raw = store.tickets.get(ticket_id)
    if not raw:
        raise HTTPException(status_code=404, detail=("ticket_not_found", f"Ticket {ticket_id} not found"))
    body = await request.json()
    text = (body.get("text") or "").strip()
    if not text:
        raise HTTPException(status_code=422, detail=("empty_message", "Message text is required"))
    ts = now_iso()
    ev = {
        "at": ts,
        "type": "centre_message",
        "actor": "centre",
        "title": "Centre messaged household",
        "detail": text,
        "ref": ticket_id,
    }
    raw["timeline"].append(ev)
    raw["card"]["updated_at"] = ts
    hh_id = raw["card"]["household"]["id"]
    store.whatsapp_threads.setdefault(hh_id, []).append({
        "id": f"wa_{uuid.uuid4().hex[:10]}",
        "direction": "out",
        "type": "text",
        "text": text,
        "media_url": None,
        "template": None,
        "at": ts,
        "ticket_id": ticket_id,
        "status": "sent",
    })
    return ev


@app.get("/v1/centre/overview")
def centre_overview(centre_id: str | None = None, centre_key: str | None = None):
    cid = store.resolve_centre_id(centre_id, centre_key)
    return store.overview[cid]


@app.get("/v1/centre/technicians")
def centre_technicians(centre_id: str | None = None, centre_key: str | None = None, cursor: str | None = None):
    cid = store.resolve_centre_id(centre_id, centre_key)
    items = [t for t in store.technicians if t["centre_id"] == cid]
    return paginate(items, cursor=cursor)


@app.get("/v1/centre/calendar")
def centre_calendar(
    date: str | None = None,
    centre_id: str | None = None,
    centre_key: str | None = None,
    cursor: str | None = None,
):
    cid = store.resolve_centre_id(centre_id, centre_key)
    slots = []
    for t in store.tickets.values():
        if t["card"]["centre_id"] == cid and t.get("visit"):
            v = t["visit"]
            if date and not (v.get("planned_start") or "").startswith(date):
                continue
            tech = store.techs_by_id.get(v["technician_id"], {})
            slots.append({
                "visit_id": v["id"],
                "ticket_id": t["card"]["id"],
                "technician_id": v["technician_id"],
                "technician_name": tech.get("name", "Technician"),
                "household_name": t["card"]["household"]["display_name"],
                "urgency_class": t["card"]["urgency_class"],
                "planned_start": v["planned_start"],
                "planned_end": v["planned_end"],
                "status": t["card"]["status"],
            })
    return paginate(slots, cursor=cursor)


@app.get("/v1/centre/stock")
def centre_stock(centre_id: str | None = None, centre_key: str | None = None, cursor: str | None = None):
    cid = store.resolve_centre_id(centre_id, centre_key)
    items = [s for s in store.stock if s["centre_id"] == cid or s["holder_id"] == cid]
    return paginate(items, cursor=cursor)


@app.get("/v1/centre/prices")
def centre_prices(centre_id: str | None = None, centre_key: str | None = None, cursor: str | None = None):
    cid = store.resolve_centre_id(centre_id, centre_key)
    items = [p for p in store.centre_prices if p["centre_id"] == cid]
    return paginate(items, cursor=cursor)


@app.get("/v1/centre/overrides")
def centre_overrides(centre_id: str | None = None, centre_key: str | None = None, cursor: str | None = None):
    items = store.overrides
    if centre_id or centre_key:
        cid = store.resolve_centre_id(centre_id, centre_key)
        items = [o for o in items if o["centre_id"] == cid]
    return paginate(items, cursor=cursor)


@app.get("/v1/appliances/{appliance_id}/timeline")
def appliance_timeline(appliance_id: str, cursor: str | None = None):
    app_obj = store.appliances_by_id.get(appliance_id)
    if not app_obj:
        raise HTTPException(status_code=404, detail=("appliance_not_found", f"Appliance {appliance_id} not found"))
    return paginate(app_obj.get("timeline", []), cursor=cursor)


@app.get("/v1/safefix")
def list_safefix(cursor: str | None = None):
    return paginate(store.safefix, cursor=cursor)


@app.get("/v1/safefix/{code}")
def get_safefix(code: str):
    sf = store.safefix_by_code.get(code)
    if not sf:
        raise HTTPException(status_code=404, detail=("safefix_not_found", f"Safe fix {code} not found"))
    return sf


# ---------------------------------------------------------------------------
# Technician Endpoints
# ---------------------------------------------------------------------------

@app.get("/v1/technicians/me/jobs")
def tech_my_jobs(
    date: str | None = None,
    technician_id: str | None = None,
    cursor: str | None = None,
):
    jobs = []
    for t in store.tickets.values():
        v = t.get("visit")
        if not v:
            continue
        if technician_id and v["technician_id"] != technician_id:
            continue
        if date and not (v.get("planned_start") or "").startswith(date):
            continue
        jobs.append({
            "visit": v,
            "ticket_card": t["card"],
            "visit_plan": t["visit_plan"],
        })
    return paginate(jobs, cursor=cursor)


@app.get("/v1/visits/{visit_id}")
def get_visit_brief(visit_id: str):
    entry = store.visits_by_id.get(visit_id)
    if not entry:
        raise HTTPException(status_code=404, detail=("visit_not_found", f"Visit {visit_id} not found"))
    tid, visit = entry
    raw = store.tickets[tid]
    slot_confirmed = raw["card"]["status"] in ("assigned", "in_progress", "closed")
    return {
        "visit": visit,
        "ticket_id": tid,
        "urgency_class": raw["card"]["urgency_class"],
        "safety_flag": raw["card"]["safety_flag"],
        "visit_plan": raw["visit_plan"],
        "already_tried": raw["tried_summary"],
        "appliance": raw["card"]["appliance"],
        "address_released": slot_confirmed,
        "household": raw["card"]["household"] if slot_confirmed else {
            "id": raw["card"]["household"]["id"],
            "display_name": raw["card"]["household"]["display_name"],
            "locality": raw["card"]["household"]["locality"],
            "pincode": raw["card"]["household"]["pincode"],
        },
        "quotes": raw["quotes"],
        "debrief": raw["debrief"],
    }


@app.post("/v1/visits/{visit_id}/check-in")
async def visit_check_in(visit_id: str, request: Request):
    entry = store.visits_by_id.get(visit_id)
    if not entry:
        raise HTTPException(status_code=404, detail=("visit_not_found", f"Visit {visit_id} not found"))
    body = await request.json()
    tid, visit = entry
    ts = now_iso()
    visit["check_in_at"] = ts
    raw = store.tickets[tid]
    raw["card"]["status"] = "in_progress"
    raw["card"]["updated_at"] = ts
    raw["timeline"].append({
        "at": ts,
        "type": "visit_check_in",
        "actor": "technician",
        "title": "Technician checked in at household",
        "detail": f"lat={body.get('lat')}, lon={body.get('lon')}",
        "ref": visit_id,
    })
    return visit


@app.post("/v1/visits/{visit_id}/parts-used")
async def visit_parts_used(visit_id: str, request: Request):
    entry = store.visits_by_id.get(visit_id)
    if not entry:
        raise HTTPException(status_code=404, detail=("visit_not_found", f"Visit {visit_id} not found"))
    body = await request.json()
    tid, visit = entry
    parts = body.get("parts", [])
    raw = store.tickets[tid]
    ts = now_iso()
    raw["timeline"].append({
        "at": ts,
        "type": "parts_used_logged",
        "actor": "technician",
        "title": f"Logged {len(parts)} part(s) used",
        "detail": json.dumps(parts),
        "ref": visit_id,
    })
    return {"visit_id": visit_id, "parts_used": parts, "recorded_at": ts}


@app.post("/v1/visits/{visit_id}/outcome")
async def visit_outcome(visit_id: str, request: Request):
    entry = store.visits_by_id.get(visit_id)
    if not entry:
        raise HTTPException(status_code=404, detail=("visit_not_found", f"Visit {visit_id} not found"))
    body = await request.json()
    tid, visit = entry
    ts = now_iso()
    visit["outcome"] = body.get("outcome", "fixed")
    visit["check_out_at"] = ts
    raw = store.tickets[tid]
    raw["card"]["updated_at"] = ts
    raw["timeline"].append({
        "at": ts,
        "type": "visit_outcome",
        "actor": "technician",
        "title": f"Visit outcome recorded: {visit['outcome']}",
        "detail": body.get("notes", ""),
        "ref": visit_id,
    })
    return visit


@app.post("/v1/visits/{visit_id}/media/upload-url")
async def visit_media_upload_url(visit_id: str, request: Request):
    if visit_id not in store.visits_by_id:
        raise HTTPException(status_code=404, detail=("visit_not_found", f"Visit {visit_id} not found"))
    body = await request.json() if await request.body() else {}
    fname = body.get("filename", "debrief.ogg")
    ref = f"gs://keepwell-mock-media/visits/{visit_id}/{uuid.uuid4().hex[:8]}_{fname}"
    return {
        "upload_url": f"http://localhost:8081/v1/mock-upload/{uuid.uuid4().hex[:8]}",
        "media_ref": ref,
        "expires_at": (datetime.now(IST) + timedelta(minutes=15)).isoformat(timespec="seconds"),
    }


@app.post("/v1/tickets/{ticket_id}/quotes")
async def create_firm_quote(ticket_id: str, request: Request):
    raw = store.tickets.get(ticket_id)
    if not raw:
        raise HTTPException(status_code=404, detail=("ticket_not_found", f"Ticket {ticket_id} not found"))
    body = await request.json()
    lines = body.get("lines", [])
    if not lines:
        raise HTTPException(status_code=422, detail=("empty_quote_lines", "At least one quote line is required"))
    total = sum(int(ln.get("amount_paise", 0)) for ln in lines)
    hh_paise = sum(int(ln.get("amount_paise", 0)) for ln in lines if ln.get("payer", "household") == "household")
    cov_paise = total - hh_paise
    prev_total = raw["quotes"][-1]["total_paise"] if raw["quotes"] else total
    variance_pct = round(((total - prev_total) / prev_total) * 100, 1) if prev_total else 0.0
    quote = {
        "id": str(uuid.uuid4()),
        "version": len(raw["quotes"]) + 1,
        "quote_type": "firm",
        "lines": lines,
        "total_paise": total,
        "household_paise": hh_paise,
        "covered_paise": cov_paise,
        "variance_pct": variance_pct,
        "approved_at": None,
        "approval_method": None,
    }
    raw["quotes"].append(quote)
    ts = now_iso()
    raw["timeline"].append({
        "at": ts,
        "type": "quote_issued",
        "actor": "technician",
        "title": f"Firm quote issued (₹{total / 100:.2f})",
        "detail": f"Variance vs estimate: {variance_pct:+.1f}%",
        "ref": quote["id"],
    })
    return quote


@app.post("/v1/visits/{visit_id}/debrief")
async def create_debrief(visit_id: str, request: Request):
    entry = store.visits_by_id.get(visit_id)
    if not entry:
        raise HTTPException(status_code=404, detail=("visit_not_found", f"Visit {visit_id} not found"))
    body = await request.json()
    tid, _visit = entry
    raw = store.tickets[tid]
    lang = body.get("language", "hi")
    plan_parts = raw["visit_plan"]["parts"] if raw.get("visit_plan") else []
    part_no = plan_parts[0]["part_no"] if plan_parts else "WC-WM-DPUMP"
    debrief = {
        "id": str(uuid.uuid4()),
        "visit_id": visit_id,
        "status": "ready",
        "language": lang,
        "transcript": "Replaced drain pump assembly and cleared coin from impeller housing; also swapped a small rubber ring.",
        "extracted": {
            "fault_found": "Impeller jammed by foreign object; pump motor windings burnt",
            "work_done": f"Replaced {part_no}, ran drain and spin verification cycle",
            "parts_used": [{"part_no": part_no, "quantity": 1}],
            "advice_for_household": "Clean drain filter every 3 months and check pockets before washing.",
            "appliance_notes": "No leaks detected after test cycle.",
            "follow_up_needed": False,
        },
        "unresolved": ["small rubber ring (unmatched in catalogue — needs checking)"],
        "confirmed_at": None,
    }
    raw["debrief"] = debrief
    raw["timeline"].append({
        "at": now_iso(),
        "type": "debrief_processed",
        "actor": "agent",
        "title": "Voice debrief extracted (1 part needs checking)",
        "detail": debrief["extracted"]["work_done"],
        "ref": debrief["id"],
    })
    return debrief


@app.post("/v1/visits/{visit_id}/debrief/confirm")
async def confirm_debrief(visit_id: str, request: Request):
    entry = store.visits_by_id.get(visit_id)
    if not entry:
        raise HTTPException(status_code=404, detail=("visit_not_found", f"Visit {visit_id} not found"))
    body = await request.json()
    tid, _visit = entry
    raw = store.tickets[tid]
    if not raw.get("debrief"):
        raise HTTPException(status_code=400, detail=("no_debrief", "No debrief exists for this visit"))
    ts = now_iso()
    if "extracted" in body:
        raw["debrief"]["extracted"] = body["extracted"]
    raw["debrief"]["status"] = "confirmed"
    raw["debrief"]["confirmed_at"] = ts
    app_ref = raw["card"].get("appliance")
    if app_ref and app_ref["id"] in store.appliances_by_id:
        store.appliances_by_id[app_ref["id"]]["timeline"].append({
            "at": ts,
            "type": "repair_completed",
            "actor": "technician",
            "title": raw["debrief"]["extracted"].get("work_done", "Repair completed"),
            "detail": raw["debrief"]["extracted"].get("fault_found", ""),
            "ref": tid,
        })
    return raw["debrief"]


@app.post("/v1/visits/{visit_id}/close/request-otp")
def request_close_otp(visit_id: str):
    entry = store.visits_by_id.get(visit_id)
    if not entry:
        raise HTTPException(status_code=404, detail=("visit_not_found", f"Visit {visit_id} not found"))
    tid, _visit = entry
    otp_ref = f"otp_{uuid.uuid4().hex[:8]}"
    code = "482910"
    expires_at = (datetime.now(IST) + timedelta(minutes=10)).isoformat(timespec="seconds")
    store.otp_store[otp_ref] = {"visit_id": visit_id, "ticket_id": tid, "code": code, "expires_at": expires_at}
    raw = store.tickets[tid]
    raw["timeline"].append({
        "at": now_iso(),
        "type": "otp_sent",
        "actor": "system",
        "title": "Closure OTP sent to household",
        "detail": f"otp_ref={otp_ref}",
        "ref": otp_ref,
    })
    return {"otp_ref": otp_ref, "expires_at": expires_at, "sandbox_code": code}


@app.post("/v1/visits/{visit_id}/close/confirm")
async def confirm_close_otp(visit_id: str, request: Request):
    entry = store.visits_by_id.get(visit_id)
    if not entry:
        raise HTTPException(status_code=404, detail=("visit_not_found", f"Visit {visit_id} not found"))
    body = await request.json()
    otp_ref = body.get("otp_ref")
    code = str(body.get("code") or "")
    rec = store.otp_store.get(otp_ref)
    if not rec or rec["visit_id"] != visit_id or (code != rec["code"] and code != "482910"):
        raise HTTPException(status_code=400, detail=("invalid_otp", "Invalid or expired OTP code"))
    tid, visit = entry
    ts = now_iso()
    visit["closure_confirmed_at"] = ts
    visit["outcome"] = visit.get("outcome") or "fixed"
    raw = store.tickets[tid]
    raw["card"]["status"] = "closed"
    raw["card"]["resolution"] = "visit"
    raw["card"]["updated_at"] = ts
    raw["timeline"].append({
        "at": ts,
        "type": "ticket_closed",
        "actor": "household",
        "title": "Ticket closed with household OTP",
        "detail": f"Confirmed via {otp_ref}",
        "ref": visit_id,
    })
    return {"status": "closed", "visit": visit, "ticket_id": tid}


@app.post("/v1/technicians/me/location")
async def update_tech_location(request: Request):
    body = await request.json()
    tech_id = body.get("technician_id") or store.technicians[0]["id"]
    if tech_id in store.techs_by_id:
        store.techs_by_id[tech_id]["last_location"] = {"lat": body.get("lat"), "lon": body.get("lon")}
        store.techs_by_id[tech_id]["last_ping_at"] = body.get("at") or now_iso()
    return {"status": "ok", "technician_id": tech_id}


# ---------------------------------------------------------------------------
# Parts Centre Endpoints
# ---------------------------------------------------------------------------

@app.get("/v1/partscentre/requests")
def list_parts_requests(cursor: str | None = None):
    return paginate(list(store.parts_requests.values()), cursor=cursor)


@app.post("/v1/partscentre/requests/{req_id}/accept")
def accept_parts_request(req_id: str):
    req = store.parts_requests.get(req_id)
    if not req:
        raise HTTPException(status_code=404, detail=("parts_request_not_found", f"Parts request {req_id} not found"))
    req["status"] = "accepted"
    return req


@app.post("/v1/partscentre/requests/{req_id}/ready")
def ready_parts_request(req_id: str):
    req = store.parts_requests.get(req_id)
    if not req:
        raise HTTPException(status_code=404, detail=("parts_request_not_found", f"Parts request {req_id} not found"))
    req["status"] = "ready"
    return req


@app.post("/v1/partscentre/requests/{req_id}/handover")
def handover_parts_request(req_id: str):
    req = store.parts_requests.get(req_id)
    if not req:
        raise HTTPException(status_code=404, detail=("parts_request_not_found", f"Parts request {req_id} not found"))
    req["status"] = "handed_over"
    return req


@app.put("/v1/partscentre/stock")
async def update_parts_stock(request: Request):
    body = await request.json()
    part_no = body.get("part_no")
    qty = int(body.get("quantity", 0))
    updated = None
    for s in store.stock:
        if s["part_no"] == part_no and s["holder_type"] == "parts_centre":
            s["quantity"] = qty
            s["as_of"] = now_iso()
            updated = s
            break
    if not updated:
        updated = {
            "id": str(uuid.uuid4()),
            "holder_type": "parts_centre",
            "holder_id": store.parts_centres[0]["id"],
            "centre_id": None,
            "part_no": part_no,
            "quantity": qty,
            "confidence": 0.95,
            "as_of": now_iso(),
        }
        store.stock.append(updated)
    return updated


# ---------------------------------------------------------------------------
# Brand & Retailer Endpoints
# ---------------------------------------------------------------------------

@app.get("/v1/brand/requests")
def list_brand_requests(brand: str | None = None, cursor: str | None = None):
    items = [
        t["card"]
        for t in store.tickets.values()
        if t["card"]["trigger"] in ("brand_forward", "retailer_handover")
    ]
    if brand:
        bl = brand.lower()
        items = [c for c in items if c["appliance"] and (c["appliance"]["brand"] or "").lower() == bl]
    return paginate(items, cursor=cursor)


@app.get("/v1/brand/analytics")
def brand_analytics(brand: str | None = None):
    apps = store.appliances
    if brand:
        apps = [a for a in apps if a["brand"].lower() == brand.lower()]
    return {
        "brand": brand or "All Brands",
        "installed_base_count": len(apps),
        "warranty_active_count": sum(1 for a in apps if a.get("warranty_end") and a["warranty_end"] >= "2026-11-21"),
        "first_time_fix": 0.84,
        "fvr_14d": 0.79,
        "self_fix_resolution": 0.28,
        "avg_turnaround_hours": 18.4,
        "top_fault_families": [
            {"fault_family": "drainage", "count": 42},
            {"fault_family": "cooling", "count": 38},
            {"fault_family": "heating", "count": 21},
        ],
    }


# ---------------------------------------------------------------------------
# Household Public Endpoints (signed magic token)
# ---------------------------------------------------------------------------

@app.post("/v1/public/session")
async def create_public_session(request: Request):
    body = await request.json()
    token = body.get("magic_token")
    hh = store.households_by_token.get(token)
    if not hh:
        raise HTTPException(status_code=404, detail=("invalid_magic_token", "Magic token not recognized"))
    return {
        "firebase_custom_token": f"mock_custom_token_{hh['id']}",
        "household_id": hh["id"],
        "expires_at": (datetime.now(IST) + timedelta(hours=24)).isoformat(timespec="seconds"),
    }


@app.get("/v1/public/home/{token}")
def get_public_home(token: str):
    hh, ticket = store.find_ticket_for_household_token(token)
    hh_apps = [a for a in store.appliances if a["household_id"] == hh["id"]]
    return {
        "household": {
            "id": hh["id"],
            "display_name": hh["display_name"],
            "language": hh["language"],
            "locality": hh["locality"],
            "pincode": hh["pincode"],
            "address_line": hh["address_line"],
        },
        "appliances": hh_apps,
        "active_ticket": ticket["card"],
        "next_due": [
            {"appliance_id": a["id"], "brand": a["brand"], "category_code": a["category_code"], "next_due_at": a["next_due_at"]}
            for a in hh_apps
            if a.get("next_due_at")
        ],
    }


@app.get("/v1/public/quotes/{token}")
def get_public_quote(token: str):
    _hh, ticket = store.find_ticket_for_household_token(token)
    latest_quote = ticket["quotes"][-1] if ticket["quotes"] else None
    latest_payment = ticket["payments"][-1] if ticket["payments"] else None
    return {
        "ticket_id": ticket["card"]["id"],
        "centre_name": store.centres_by_id[ticket["card"]["centre_id"]]["name"],
        "quote": latest_quote,
        "payment": latest_payment,
    }


@app.post("/v1/public/quotes/{token}/approve")
def approve_public_quote(token: str):
    _hh, ticket = store.find_ticket_for_household_token(token)
    if not ticket["quotes"]:
        raise HTTPException(status_code=404, detail=("quote_not_found", "No quote found for ticket"))
    ts = now_iso()
    q = ticket["quotes"][-1]
    q["approved_at"] = ts
    q["approval_method"] = "magic_link"
    ticket["timeline"].append({
        "at": ts,
        "type": "quote_approved",
        "actor": "household",
        "title": f"Household approved quote (₹{q['total_paise'] / 100:.2f})",
        "detail": "Approved via magic link",
        "ref": q["id"],
    })
    return q


@app.post("/v1/public/otp/{token}/confirm")
async def confirm_public_otp(token: str, request: Request):
    _hh, ticket = store.find_ticket_for_household_token(token)
    body = await request.json() if await request.body() else {}
    ts = now_iso()
    if ticket.get("visit"):
        ticket["visit"]["closure_confirmed_at"] = ts
    ticket["card"]["status"] = "closed"
    ticket["card"]["resolution"] = "visit"
    return {"status": "confirmed", "ticket_id": ticket["card"]["id"], "confirmed_at": ts, "code": body.get("code", "482910")}


@app.post("/v1/public/quotes/{token}/pay-intent")
async def create_pay_intent(token: str, request: Request):
    _hh, ticket = store.find_ticket_for_household_token(token)
    body = await request.json()
    method = body.get("method", "upi_intent")
    if method not in ("upi_intent", "google_pay"):
        raise HTTPException(status_code=422, detail=("invalid_payment_method", "Method must be upi_intent or google_pay"))
    q = ticket["quotes"][-1]
    amount = q["household_paise"]
    pid = str(uuid.uuid4())
    ts = now_iso()
    centre_name = store.centres_by_id[ticket["card"]["centre_id"]]["name"]
    intent = {
        "id": pid,
        "quote_id": q["id"],
        "amount_paise": amount,
        "status": "pending",
        "method": method,
        "upi_intent_url": f"upi://pay?pa=keepwell@okaxis&pn=Keepwell&am={amount / 100:.2f}&cu=INR&tr={pid[:12]}" if method == "upi_intent" else None,
        "google_pay": {
            "environment": "TEST",
            "merchant_name": centre_name,
            "merchant_id": "BCR2DN4TKEEPWELL",
            "gateway": "example",
            "gateway_merchant_id": "exampleGatewayMerchantId",
            "transaction_info": {
                "currency_code": "INR",
                "total_price_status": "FINAL",
                "total_price": f"{amount / 100:.2f}",
            },
        } if method == "google_pay" else None,
        "payment_ref": None,
        "created_at": ts,
        "expires_at": (datetime.now(IST) + timedelta(minutes=30)).isoformat(timespec="seconds"),
        "paid_at": None,
    }
    ticket["payments"].append(intent)
    ticket["timeline"].append({
        "at": ts,
        "type": "payment_initiated",
        "actor": "household",
        "title": f"Payment initiated via {method} (₹{amount / 100:.2f})",
        "detail": pid,
        "ref": pid,
    })
    return intent


@app.get("/v1/public/quotes/{token}/payment")
def get_public_payment(token: str):
    _hh, ticket = store.find_ticket_for_household_token(token)
    if not ticket["payments"]:
        raise HTTPException(status_code=404, detail=("payment_not_found", "No payment intent exists"))
    return ticket["payments"][-1]


@app.post("/v1/public/quotes/{token}/payment/sandbox-complete")
async def sandbox_complete_payment(token: str, request: Request):
    _hh, ticket = store.find_ticket_for_household_token(token)
    body = await request.json()
    payment_id = body.get("payment_id")
    result = body.get("result", "success")
    intent = next((p for p in reversed(ticket["payments"]) if not payment_id or p["id"] == payment_id), None)
    if not intent:
        raise HTTPException(status_code=404, detail=("payment_not_found", "Payment intent not found"))
    ts = now_iso()
    if result == "success":
        intent["status"] = "paid"
        intent["paid_at"] = ts
        intent["payment_ref"] = f"SANDBOX-{uuid.uuid4().hex[:8].upper()}"
        ticket["timeline"].append({
            "at": ts,
            "type": "payment_confirmed",
            "actor": "system",
            "title": f"Payment confirmed ({intent['payment_ref']})",
            "detail": f"₹{intent['amount_paise'] / 100:.2f}",
            "ref": intent["id"],
        })
    else:
        intent["status"] = "failed"
        ticket["timeline"].append({
            "at": ts,
            "type": "payment_failed",
            "actor": "system",
            "title": "Payment failed in sandbox",
            "detail": body.get("reason", "Simulated failure"),
            "ref": intent["id"],
        })
    return intent


@app.post("/v1/channels/payments/webhook")
async def payments_webhook(request: Request):
    body = await request.json()
    pid = body.get("payment_id")
    ts = now_iso()
    for t in store.tickets.values():
        for p in t["payments"]:
            if p["id"] == pid:
                p["status"] = "paid"
                p["paid_at"] = ts
                p["payment_ref"] = body.get("payment_ref", f"WH-{uuid.uuid4().hex[:8].upper()}")
                return {"status": "processed", "payment_id": pid}
    return {"status": "ignored", "payment_id": pid}


# ---------------------------------------------------------------------------
# Channels Endpoints
# ---------------------------------------------------------------------------

@app.get("/v1/channels/whatsapp/webhook")
def whatsapp_verify(
    hub_mode: str | None = Query(default=None, alias="hub.mode"),
    hub_challenge: str | None = Query(default=None, alias="hub.challenge"),
):
    return PlainTextResponse(hub_challenge or "ok")


@app.post("/v1/channels/whatsapp/webhook")
async def whatsapp_inbound_webhook(request: Request):
    _body = await request.json()
    return {"status": "received"}


@app.post("/v1/channels/whatsapp/simulator/media")
async def whatsapp_sim_media(request: Request):
    _ = await request.body()
    mid = f"media_{uuid.uuid4().hex[:10]}"
    return {"media_id": mid, "media_url": f"http://localhost:8081/v1/mock-media/{mid}"}


@app.post("/v1/channels/whatsapp/simulator/inbound")
async def whatsapp_sim_inbound(request: Request):
    body = await request.json()
    to_number = body.get("to_number", "")
    sender_name = body.get("sender_profile_name") or "Household"
    messages = body.get("messages", [])
    text = " ".join(
        m.get("text", {}).get("body", "") for m in messages if m.get("type") == "text"
    ).strip() or "Media message received"

    # Find receiving centre by to_number or default c_fw
    cid = store.centres_by_key["c_fw"]["id"]
    for c in store.centres:
        for ch in c["channels"]:
            if ch["number_ref"] == to_number:
                cid = c["id"]
                break

    hh = next((h for h in store.households if h["display_name"].lower() == sender_name.lower()), store.households[0])
    ts = now_iso()
    store.whatsapp_threads.setdefault(hh["id"], []).append({
        "id": f"wa_in_{uuid.uuid4().hex[:8]}",
        "direction": "in",
        "type": "text",
        "text": text,
        "media_url": None,
        "template": None,
        "at": ts,
        "ticket_id": None,
        "status": "delivered",
    })

    # Safety detection for demo
    is_safety = any(w in text.lower() for w in ("shock", "smoke", "spark", "burn", "gas leak"))
    reply_text = (
        "Please stop using it and switch it off at the wall. A technician will come as soon as possible."
        if is_safety
        else f"Thank you {hh['display_name']}. Are you okay to try a quick, safe fix yourself first?"
    )
    store.whatsapp_threads[hh["id"]].append({
        "id": f"wa_out_{uuid.uuid4().hex[:8]}",
        "direction": "out",
        "type": "text",
        "text": reply_text,
        "media_url": None,
        "template": "safety_stop" if is_safety else "gate_1",
        "at": ts,
        "ticket_id": None,
        "status": "sent",
    })
    return {
        "status": "received",
        "centre_id": cid,
        "household_id": hh["id"],
        "safety_flag": is_safety,
        "reply": reply_text,
    }


@app.post("/v1/channels/brand/requests", status_code=202)
async def brand_forward_intake(request: Request, x_keepwell_key: str | None = Header(default=None)):
    body = await request.json()
    brand_name = (body.get("brand") or "zenith").lower()
    centre_key = body.get("centre_key") or ("c_zn" if brand_name == "zenith" else "c_cc")
    cid = store.resolve_centre_id(centre_key=centre_key)
    centre = store.centres_by_id[cid]
    is_auth = any(
        a["brand"].lower() == brand_name and a["level"] == "authorised_service"
        for a in centre["authorisations"]
    )
    ticket_id = str(uuid.uuid4())
    if not is_auth and body.get("claimed_warranty") == "in_warranty":
        return JSONResponse(
            status_code=202,
            content={
                "ticket_id": ticket_id,
                "status": "declined",
                "declined_reason": f"{centre['name']} is not an authorised warranty centre for {brand_name.title()}.",
            },
        )
    return JSONResponse(
        status_code=202,
        content={"ticket_id": ticket_id, "status": "received", "declined_reason": None},
    )


@app.post("/v1/channels/retailer/handovers", status_code=202)
async def retailer_handover_intake(request: Request, x_keepwell_key: str | None = Header(default=None)):
    _body = await request.json()
    return JSONResponse(
        status_code=202,
        content={"ticket_id": str(uuid.uuid4()), "status": "received", "declined_reason": None},
    )


# ---------------------------------------------------------------------------
# Admin & Demo Endpoints
# ---------------------------------------------------------------------------

@app.get("/v1/admin/demo/cases")
def admin_demo_cases(cursor: str | None = None):
    cases = [
        {k: v for k, v in c.items() if k != "inbox_event"}
        for c in store.demo_cases
    ]
    return paginate(cases, cursor=cursor)


@app.post("/v1/admin/demo/play-case")
async def admin_play_case(request: Request):
    body = await request.json()
    case_id = body.get("case_id")
    case = next((c for c in store.demo_cases if c["case_id"] == case_id), None)
    if not case:
        raise HTTPException(status_code=404, detail=("case_not_found", f"Case {case_id} not found"))
    store.active_case_id = case_id
    tid = case["ticket_id"]
    ts = now_iso()
    if tid in store.tickets:
        store.tickets[tid]["card"]["updated_at"] = ts
        store.tickets[tid]["timeline"].append({
            "at": ts,
            "type": "conversation_started",
            "actor": "system",
            "title": f"Demo replayed case {case_id}",
            "detail": case["summary"],
            "ref": tid,
        })
    return {"status": "playing", "case_id": case_id, "ticket_id": tid, "centre_key": case["centre_key"]}


@app.get("/v1/admin/demo/households")
def admin_demo_households(centre_key: str | None = None, cursor: str | None = None):
    items = store.demo_households
    if centre_key:
        items = [h for h in items if h["centre_key"] == centre_key]
    return paginate(items, cursor=cursor)


@app.post("/v1/admin/demo/reset")
def admin_demo_reset():
    store.reset()
    return {"status": "reset", "reset_at": store.reset_at, "tickets": len(store.tickets)}


@app.post("/v1/admin/projection/rebuild")
def admin_projection_rebuild():
    return {"status": "rebuilt", "centres": len(store.centres), "tickets": len(store.tickets), "at": now_iso()}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("mocks.rest.server:app", host="0.0.0.0", port=int(os.getenv("MOCK_REST_PORT", "8081")), reload=False)
