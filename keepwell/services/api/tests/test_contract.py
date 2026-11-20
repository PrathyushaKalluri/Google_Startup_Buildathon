"""Comprehensive Contract C5, C6, C7, C8 & RLS tests for Keepwell REST API v1."""
from __future__ import annotations

import hashlib
import hmac
import json

import pytest
from fastapi.testclient import TestClient

from services.agents.engines.payments import sign_webhook_payload
from services.api.main import app
from services.common.config import settings
from services.common.crypto import mint_magic_token
from services.common.db import get_rls_session
from services.live.tools.scripted_client import run_c03_scripted_live_call

client = TestClient(app)

CONSOLE_FW = {"Authorization": "Bearer demo:console.c_fw@keepwell.demo"}
CONSOLE_AV = {"Authorization": "Bearer demo:console.c_av@keepwell.demo"}
TECH1_FW = {"Authorization": "Bearer demo:tech1.c_fw@keepwell.demo"}
PARTS_AUTH = {"Authorization": "Bearer demo:parts.demo@keepwell.demo"}
BRAND_AV = {"Authorization": "Bearer demo:brand.aerovane@keepwell.demo"}
PLATFORM_AUTH = {"Authorization": "Bearer demo:platform@keepwell.demo"}


def test_api_fails_at_startup_when_database_url_not_postgres(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "database_url", "mysql://localhost/wrong")
    with pytest.raises(RuntimeError, match="requires PostgreSQL 16"):
        with TestClient(app):
            pass


def test_system_health_ready_version_openapi_and_mcp() -> None:
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

    r = client.get("/readyz")
    assert r.status_code == 200
    assert r.json()["centres"] == 9

    r = client.get("/v1/meta/version")
    assert r.status_code == 200
    assert r.json()["api_version"] == "v1"

    r = client.get("/openapi.json")
    assert r.status_code == 200
    spec = r.json()
    assert "/v1/tickets" in spec["paths"]
    assert "/v1/admin/demo/cases" in spec["paths"]

    # MCP server mounted at /mcp
    r = client.get("/mcp/tools")
    assert r.status_code == 200
    assert len(r.json()["tools"]) == 24

    r = client.post("/mcp", json={"jsonrpc": "2.0", "id": "1", "method": "tools/list", "params": {}})
    assert r.status_code == 200
    assert len(r.json()["result"]["tools"]) == 24


def test_consistent_error_envelope() -> None:
    # Missing auth -> 401 with Contract C5 error envelope
    r = client.get("/v1/tickets")
    assert r.status_code == 401
    body = r.json()
    assert "error" in body
    assert set(body["error"].keys()) == {"code", "message", "field", "request_id"}
    assert body["error"]["code"] == "unauthorized"

    # Not found -> 404 with Contract C5 error envelope
    r = client.get("/v1/tickets/non-existent-id", headers=CONSOLE_FW)
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "ticket_not_found"


def test_c03_live_ws_scripted_and_console_detail_and_overrides() -> None:
    # 1. Run full scripted C03 Live WS call
    ws_res = run_c03_scripted_live_call(client)
    tid = ws_res["ticket_id"]

    # 2. Fetch TicketDetail from c_fw console
    r = client.get(f"/v1/tickets/{tid}", headers=CONSOLE_FW)
    assert r.status_code == 200
    detail = r.json()
    for key in (
        "card",
        "case_card",
        "urgency",
        "gates",
        "clarifying_qa",
        "fix_attempts",
        "tried_summary",
        "diagnosis",
        "visit_plan",
        "candidates",
        "slot_proposals",
        "quotes",
        "payments",
        "debrief",
        "visit",
        "timeline",
        "authority",
    ):
        assert key in detail, f"Missing TicketDetail key: {key}"
    assert detail["card"]["id"] == tid
    assert len(detail["fix_attempts"]) >= 1
    assert len(detail["tried_summary"]) >= 1

    # 3. RLS cross-centre check: c_av MUST NOT see c_fw's ticket
    r_other = client.get(f"/v1/tickets/{tid}", headers=CONSOLE_AV)
    assert r_other.status_code == 404

    # 4. Reclassify urgency (assessed_by='centre_console')
    r = client.post(
        f"/v1/tickets/{tid}/reclassify-urgency",
        headers=CONSOLE_FW,
        json={"class": "urgent", "reason": "Flooding risk reported by household"},
    )
    assert r.status_code == 200
    urg_list = r.json()["urgency"]
    assert any(u["assessed_by"] == "centre_console" and u["class"] == "urgent" for u in urg_list)

    # 5. Reassign technician (chosen_by='centre_console', emits reassigned)
    techs_r = client.get("/v1/centre/technicians", headers=CONSOLE_FW)
    assert techs_r.status_code == 200
    tech_items = techs_r.json()["items"]
    assert len(tech_items) >= 1
    target_tech_id = tech_items[-1]["id"]

    r = client.post(
        f"/v1/tickets/{tid}/reassign",
        headers=CONSOLE_FW,
        json={
            "technician_id": target_tech_id,
            "slot_start": "2026-11-21T14:00:00+05:30",
            "slot_end": "2026-11-21T16:00:00+05:30",
            "reason": "Closer to Kukatpally",
        },
    )
    assert r.status_code == 200
    assert any(c["chosen_by"] == "centre_console" for c in r.json()["candidates"])
    assert any(ev["type"] == "reassigned" for ev in r.json()["timeline"])

    # 6. Rerun diagnosis & send message
    r = client.post(f"/v1/tickets/{tid}/rerun-diagnosis", headers=CONSOLE_FW)
    assert r.status_code == 200
    assert r.json()["visit_plan"]["version"] >= 2

    r = client.post(f"/v1/tickets/{tid}/message", headers=CONSOLE_FW, json={"text": "Technician is on the way"})
    assert r.status_code == 200
    assert r.json()["actor"] == "centre"

    # 7. Console board ordering, overview KPIs, calendar, stock, prices, overrides, safefix
    r = client.get("/v1/tickets", headers=CONSOLE_FW)
    assert r.status_code == 200
    assert "items" in r.json() and "next_cursor" in r.json()

    r = client.get("/v1/centre/overview", headers=CONSOLE_FW)
    assert r.status_code == 200
    ov = r.json()
    for k in (
        "open_by_class",
        "first_time_fix",
        "fvr_14d",
        "self_fix_resolution",
        "gate_funnel",
        "urgency_agreement",
        "override_rate",
        "parts_ready_at_visit",
        "jobs_per_technician_day",
    ):
        assert k in ov

    for ep in ("/v1/centre/calendar", "/v1/centre/stock", "/v1/centre/prices", "/v1/centre/overrides", "/v1/safefix"):
        resp = client.get(ep, headers=CONSOLE_FW)
        assert resp.status_code == 200
        assert "items" in resp.json()

    sf_code = client.get("/v1/safefix", headers=CONSOLE_FW).json()["items"][0]["code"]
    assert client.get(f"/v1/safefix/{sf_code}", headers=CONSOLE_FW).status_code == 200

    # Appliance timeline via read_shared_history
    app_id = detail["card"]["appliance"]["id"]
    r_tl = client.get(f"/v1/appliances/{app_id}/timeline", headers=CONSOLE_FW)
    assert r_tl.status_code == 200
    assert "items" in r_tl.json()


def test_technician_flow_payment_sandbox_debrief_and_otp_close() -> None:
    # Create a ticket via simulator inbound on c_fw
    with get_rls_session(role="platform") as db:
        row = db.raw_query(
            """
            SELECT cc.number_ref FROM centre_channel cc
            JOIN service_centre sc ON sc.id = cc.centre_id
            WHERE sc.name LIKE 'Frost and Wave%' LIMIT 1
            """
        )[0]
        fw_num = row["number_ref"]

    r = client.post(
        "/v1/channels/whatsapp/simulator/inbound",
        json={
            "to_number": fw_num,
            "from_phone": "+91 50971 16577",
            "sender_profile_name": "Sunita Sharma",
            "messages": [{"type": "text", "text": {"body": "Wavecrest washer not draining E21"}}],
        },
    )
    assert r.status_code == 200
    tid = r.json()["ticket_id"]
    hh_id = r.json()["household_id"]
    assert tid

    detail = client.get(f"/v1/tickets/{tid}", headers=CONSOLE_FW).json()
    visit_id = detail["visit"]["id"]

    # Technician jobs, location, device registration
    assert client.get("/v1/technicians/me/jobs", headers=TECH1_FW).status_code == 200
    assert client.post("/v1/technicians/me/location", headers=TECH1_FW, json={"lat": 17.48, "lon": 78.39}).status_code == 200
    assert client.post("/v1/devices", headers=TECH1_FW, json={"token": "fcm-test-token", "platform": "android"}).status_code == 200

    # Visit brief logs access_log when address/phone released
    brief_r = client.get(f"/v1/visits/{visit_id}", headers=TECH1_FW)
    assert brief_r.status_code == 200
    assert brief_r.json()["address_released"] is True
    with get_rls_session(role="platform") as db:
        logs = db.raw_query("SELECT * FROM access_log WHERE record_table = 'visit' AND record_id = %s", (visit_id,))
        assert len(logs) >= 1

    # Check-in, upload-url, outcome
    assert client.post(f"/v1/visits/{visit_id}/check-in", headers=TECH1_FW, json={"lat": 17.48, "lon": 78.39}).status_code == 200
    up = client.post(f"/v1/visits/{visit_id}/media/upload-url", headers=TECH1_FW, json={"kind": "debrief_audio", "content_type": "audio/ogg"})
    assert up.status_code == 200
    media_ref = up.json()["media_ref"]
    assert client.post(
        f"/v1/visits/{visit_id}/outcome",
        headers=TECH1_FW,
        json={"outcome": "fixed", "outcome_notes": "Replaced drain pump"},
    ).status_code == 200

    # Firm quote + variance
    fq_r = client.post(
        f"/v1/tickets/{tid}/quotes",
        headers=TECH1_FW,
        json={
            "lines": [
                {"kind": "visit_fee", "description": "Visit fee", "amount_paise": 29900, "payer": "household"},
                {"kind": "labour", "description": "Drain pump replacement", "amount_paise": 55000, "payer": "household"},
            ]
        },
    )
    assert fq_r.status_code == 200
    fq = fq_r.json()
    assert fq["quote_type"] == "firm"
    assert "variance_pct" in fq
    quote_id = fq["id"]

    # Public household session, home memory, quote approve, pay-intent, sandbox-complete
    hh_token = mint_magic_token(hh_id, scope="household", ttl_seconds=3600, extra={"household_id": hh_id})
    q_token = mint_magic_token(quote_id, scope="quote", ttl_seconds=3600, extra={"quote_id": quote_id, "household_id": hh_id})

    sess = client.post("/v1/public/session", json={"magic_token": hh_token})
    assert sess.status_code == 200
    assert sess.json()["household_id"] == hh_id

    home = client.get(f"/v1/public/home/{hh_token}")
    assert home.status_code == 200
    assert len(home.json()["appliances"]) >= 1

    assert client.get(f"/v1/public/quotes/{q_token}").status_code == 200
    apr = client.post(f"/v1/public/quotes/{q_token}/approve")
    assert apr.status_code == 200
    assert apr.json()["approved_at"] is not None

    pi_r = client.post(f"/v1/public/quotes/{q_token}/pay-intent", json={"method": "upi_intent"})
    assert pi_r.status_code == 200
    pi = pi_r.json()
    assert pi["upi_intent_url"].startswith("upi://pay?")

    assert client.get(f"/v1/public/quotes/{q_token}/payment").status_code == 200

    sc_r = client.post(
        f"/v1/public/quotes/{q_token}/payment/sandbox-complete",
        json={"payment_id": pi["id"], "result": "success"},
    )
    assert sc_r.status_code == 200
    assert sc_r.json()["status"] == "paid"

    # INVARIANT: Payment NEVER closes the ticket!
    t_after_pay = client.get(f"/v1/tickets/{tid}", headers=CONSOLE_FW).json()
    assert t_after_pay["card"]["status"] != "closed"

    # Also test payment webhook with HMAC (and verify still not closed)
    wh_payload = json.dumps({"payment_id": pi["id"], "status": "paid", "payment_ref": "WH-REF-001"}).encode("utf-8")
    sig = sign_webhook_payload(wh_payload, settings.payment_webhook_secret)
    wh_r = client.post(
        "/v1/channels/payments/webhook",
        content=wh_payload,
        headers={"Content-Type": "application/json", "X-Keepwell-Signature": sig},
    )
    assert wh_r.status_code == 200
    assert wh_r.json()["ticket_closed"] is False

    # Debrief + confirm
    deb_r = client.post(
        f"/v1/visits/{visit_id}/debrief",
        headers=TECH1_FW,
        json={"media_ref": media_ref, "language": "en", "transcript": "Cleaned sump and replaced pump, tested spin cycle."},
    )
    assert deb_r.status_code == 200
    deb = deb_r.json()
    assert deb["status"] == "ready"

    conf_r = client.post(
        f"/v1/visits/{visit_id}/debrief/confirm",
        headers=TECH1_FW,
        json={"extracted": deb["extracted"]},
    )
    assert conf_r.status_code == 200
    assert conf_r.json()["status"] == "confirmed"

    # Closure by OTP ONLY
    otp_req = client.post(f"/v1/visits/{visit_id}/close/request-otp", headers=TECH1_FW)
    assert otp_req.status_code == 200
    otp_ref = otp_req.json()["otp_ref"]
    sandbox_code = otp_req.json()["sandbox_code"]

    # Wrong code fails
    bad = client.post(f"/v1/visits/{visit_id}/close/confirm", headers=TECH1_FW, json={"otp_ref": otp_ref, "code": "000000"})
    assert bad.status_code == 400

    # Right code closes ticket
    ok = client.post(f"/v1/visits/{visit_id}/close/confirm", headers=TECH1_FW, json={"otp_ref": otp_ref, "code": sandbox_code})
    assert ok.status_code == 200
    assert ok.json()["closed"] is True

    t_closed = client.get(f"/v1/tickets/{tid}", headers=CONSOLE_FW).json()
    assert t_closed["card"]["status"] == "closed"


def test_c18_brand_authority_decline_and_retailer_and_whatsapp_webhook() -> None:
    # C18: Aerovane warranty forwarded to Cool Craft (independent) -> 202 declined
    c18_payload = {
        "kind": "brand_request",
        "brand": "aerovane",
        "ref": "AV-SRQ-557019",
        "complaint": "AC cooling very weak since 3 days, claims warranty",
        "claimed_warranty": "in_warranty",
        "brand_note": "Forwarded to Cool Craft Appliance Services for scheduling.",
        "customer": {"name": "Deepak Chowdary", "phone": "+91 58028 98021"},
    }
    r = client.post("/v1/channels/brand/requests", headers={"X-Keepwell-Key": "kw-brand-aerovane"}, json=c18_payload)
    assert r.status_code == 202
    assert r.json()["status"] == "declined"
    assert r.json()["ticket_id"] is None
    assert r.json()["declined_reason"]

    # Retailer handover -> 202 received
    c20_payload = {
        "kind": "retailer_handover",
        "retailer": "Sri Sai Electronics, Kukatpally",
        "order_ref": "SSE-ORD-77120",
        "requested_job": "installation",
        "notes": "Front-load washer delivered yesterday, needs inlet and outlet connection.",
        "customer": {"name": "Mahesh Raj", "phone": "+91 58800 49668"},
    }
    r = client.post("/v1/channels/retailer/handovers", headers={"X-Keepwell-Key": "kw-retailer-demo"}, json=c20_payload)
    assert r.status_code == 202
    assert r.json()["status"] == "received"
    assert r.json()["ticket_id"]

    # WhatsApp webhook verify & HMAC inbound
    r_ver = client.get(
        "/v1/channels/whatsapp/webhook",
        params={"hub.mode": "subscribe", "hub.verify_token": settings.whatsapp_verify_token, "hub.challenge": "998877"},
    )
    assert r_ver.status_code == 200
    assert r_ver.text == "998877"

    wa_body = json.dumps({"entry": []}).encode("utf-8")
    wa_sig = "sha256=" + hmac.new(settings.whatsapp_app_secret.encode("utf-8"), wa_body, hashlib.sha256).hexdigest()
    r_wa = client.post("/v1/channels/whatsapp/webhook", content=wa_body, headers={"X-Hub-Signature-256": wa_sig})
    assert r_wa.status_code == 200


def test_parts_centre_brand_and_admin_endpoints() -> None:
    # Parts centre
    reqs = client.get("/v1/partscentre/requests", headers=PARTS_AUTH)
    assert reqs.status_code == 200
    items = reqs.json()["items"]
    if items:
        rid = items[0]["id"]
        assert client.post(f"/v1/partscentre/requests/{rid}/accept", headers=PARTS_AUTH).json()["status"] == "accepted"
        assert client.post(f"/v1/partscentre/requests/{rid}/ready", headers=PARTS_AUTH).json()["status"] == "ready"
        assert client.post(f"/v1/partscentre/requests/{rid}/handover", headers=PARTS_AUTH).json()["status"] == "handed_over"

    with get_rls_session(role="platform") as db:
        part_no = db.raw_query("SELECT part_no FROM part_catalogue LIMIT 1")[0]["part_no"]
    st = client.put("/v1/partscentre/stock", headers=PARTS_AUTH, json={"part_no": part_no, "quantity": 12})
    assert st.status_code == 200
    assert st.json()["quantity"] == 12

    # Brand endpoints
    assert client.get("/v1/brand/requests", headers=BRAND_AV).status_code == 200
    ba = client.get("/v1/brand/analytics", headers=BRAND_AV)
    assert ba.status_code == 200
    assert "installed_base" in ba.json() and "service_quality" in ba.json()

    # Admin & Demo endpoints (works with or without header in DEMO_MODE)
    cases = client.get("/v1/admin/demo/cases")
    assert cases.status_code == 200
    case_items = cases.json()["items"]
    assert len(case_items) == 20
    c03 = next(c for c in case_items if c["case_id"] == "C03")
    assert c03["stage_candidate"] is True

    play = client.post("/v1/admin/demo/play-case", json={"case_id": "C02"})
    assert play.status_code == 200
    assert play.json()["ticket_id"]

    hh = client.get("/v1/admin/demo/households", params={"centre_key": "c_fw"})
    assert hh.status_code == 200
    assert len(hh.json()["items"]) >= 1
    assert "magic_token" in hh.json()["items"][0]

    reb = client.post("/v1/admin/projection/rebuild", headers=PLATFORM_AUTH)
    assert reb.status_code == 200
    assert reb.json()["counts"]["tickets"] > 0

    rep = client.post("/v1/admin/demo/replay-call")
    assert rep.status_code == 200
    assert len(rep.json()["events"]) > 0
