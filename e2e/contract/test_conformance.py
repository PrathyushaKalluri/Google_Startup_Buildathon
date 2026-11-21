"""C2 contract conformance: REST paths, consumer (Dart) paths, event catalogue, Firestore shapes, CORS."""
from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from services.api.main import app

ROOT = Path(__file__).resolve().parents[2]
client = TestClient(app)
PLATFORM = {"Authorization": "Bearer demo:platform@keepwell.demo"}

EVENT_TYPES = [
    "conversation_started", "recording_notice_logged", "household_identified", "appliance_identified",
    "authority_checked", "urgency_assessed", "safety_stop_sent", "clarifying_asked", "clarifying_answered",
    "gate_asked", "gate_answered", "modality_changed", "fix_offered", "fix_step", "fix_result",
    "diagnosis_updated", "visit_plan_ready", "candidates_scored", "slots_offered", "technician_assigned",
    "reassigned", "quote_issued", "quote_approved", "payment_initiated", "payment_confirmed", "payment_failed",
    "debrief_processed", "otp_sent", "ticket_closed", "brand_request_received", "brand_request_declined",
    "retailer_handover_received", "shared_history_read", "error_notice",
]


def _norm(path: str) -> str:
    path = re.sub(r"\$\{?[A-Za-z_\.]+\}?", "{x}", path)
    path = re.sub(r"\{[^}]+\}", "{x}", path)
    return path.rstrip("/") or "/"


def _contract_endpoints() -> set[tuple[str, str]]:
    text = (ROOT / "contract" / "SHARED_CONTRACT.md").read_text()
    sec = text.split("### 5.2 Endpoints", 1)[1].split("### 5.3", 1)[0]
    found: set[tuple[str, str]] = set()
    for m in re.finditer(r"`(GET/POST|GET|POST|PUT) (/[^\s`?]+)", sec):
        methods = ("GET", "POST") if m.group(1) == "GET/POST" else (m.group(1),)
        for mth in methods:
            found.add((mth, "/v1" + m.group(2)))
    for m in re.finditer(r"`POST (/partscentre/requests/\{id\}/)accept\|ready\|handover", sec):
        for tail in ("accept", "ready", "handover"):
            found.add(("POST", "/v1" + m.group(1) + tail))
    return {(mth, _norm(p)) for mth, p in found if "|" not in p}


def _openapi_endpoints() -> set[tuple[str, str]]:
    spec = app.openapi()
    return {(m.upper(), _norm(p)) for p, ops in spec["paths"].items() for m in ops if m in ("get", "post", "put")}


def test_every_contract_endpoint_exists_in_openapi() -> None:
    contract, actual = _contract_endpoints(), _openapi_endpoints()
    missing = sorted(e for e in contract if e not in actual and e[1] != "/v1/live/call")
    assert len(contract) >= 45, f"contract parser found only {len(contract)} endpoints"
    assert not missing, f"contract endpoints missing from Part A openapi: {missing}"


def test_every_dart_client_call_exists_in_part_a() -> None:
    src = (ROOT / "apps/kw_client/lib/src/api/kw_api_client.dart").read_text()
    calls = set()
    for m in re.finditer(r"'(GET|POST|PUT)',\s*\n?\s*(?:'|\")(/[^'\"]*)(?:'|\")", src):
        raw = _norm(m.group(2).split("?")[0])
        prefix = "" if raw in ("/healthz", "/readyz") else "/v1"
        calls.add((m.group(1), prefix + raw))
    actual = _openapi_endpoints()
    missing = sorted(c for c in calls if c not in actual)
    assert len(calls) >= 40, f"parsed only {len(calls)} dart calls"
    assert not missing, f"Part B calls endpoints Part A does not serve: {missing}"


def test_committed_openapi_matches_live_app() -> None:
    import json

    committed = json.loads((ROOT / "services/api/openapi.json").read_text())
    assert set(committed["paths"]) == set(app.openapi()["paths"])


def test_error_envelope_and_request_id() -> None:
    r = client.get("/v1/tickets/not-a-uuid", headers=PLATFORM)
    body = r.json()
    assert r.status_code == 404
    assert set(body["error"]) >= {"code", "message", "field", "request_id"}


def test_cors_allows_four_hosting_origins() -> None:
    for site in ("console", "field", "household", "brand"):
        origin = f"https://kw-{site}-0527.web.app"
        r = client.options(
            "/v1/meta/version",
            headers={"Origin": origin, "Access-Control-Request-Method": "GET", "Access-Control-Request-Headers": "authorization"},
        )
        assert r.headers.get("access-control-allow-origin") in (origin, "*"), f"CORS blocked for {origin}: {r.status_code}"


def test_c03_emits_every_event_the_stage_view_needs() -> None:
    from services.live.tools.scripted_client import run_c03_scripted_live_call

    res = run_c03_scripted_live_call(client)
    needed = {
        "conversation_started", "recording_notice_logged", "gate_asked", "modality_changed",
        "household_identified", "appliance_identified", "authority_checked", "urgency_assessed",
        "fix_offered", "fix_step", "fix_result", "diagnosis_updated", "visit_plan_ready",
        "candidates_scored", "slots_offered", "technician_assigned", "quote_issued",
    }
    assert needed <= set(res["event_types"]), needed - set(res["event_types"])
    assert set(res["event_types"]) <= set(EVENT_TYPES) | {"event"}, set(res["event_types"]) - set(EVENT_TYPES)


def test_projection_documents_match_contract_section_6() -> None:
    from services.worker.projections import projection_store

    r = client.post("/v1/admin/projection/rebuild", headers=PLATFORM)
    assert r.status_code == 200
    ticket_docs = [v for k, v in projection_store.docs.items() if "/tickets/" in k]
    assert ticket_docs
    need = {"id", "status", "urgency_class", "unread", "next_action", "payment_status", "last_event_at"}
    assert need <= set(ticket_docs[0]), need - set(ticket_docs[0])
    feed = [v for k, v in projection_store.docs.items() if "/feed/" in k]
    for ev in feed[:50]:
        assert {"id", "at", "centre_id", "type", "actor", "title", "detail", "payload"} <= set(ev)


def test_section_11_metrics_and_firestore_rules() -> None:
    from services.common.db import get_rls_session

    ov = client.get("/v1/centre/overview", headers={"Authorization": "Bearer demo:console.c_fw@keepwell.demo"}).json()
    for k in ("open_by_class", "first_time_fix", "fvr_14d", "self_fix_resolution", "gate_funnel", "jobs_per_technician_day"):
        assert k in ov, f"missing KPI {k} in /centre/overview"

    with get_rls_session(role="platform") as db:
        fvr_cnt = db.raw_query("SELECT count(*) AS c FROM fvr_14d")[0]["c"]
        ftf_cnt = db.raw_query("SELECT count(*) AS c FROM first_visit_outcome")[0]["c"]
        assert int(fvr_cnt) > 0 and int(ftf_cnt) > 0

    rules = (ROOT / "infra/frontend/firestore.rules").read_text()
    assert "allow write: if false" in rules
    assert "request.auth.token.centre_id == cid" in rules
    assert "request.auth.token.household_id == hid" in rules
