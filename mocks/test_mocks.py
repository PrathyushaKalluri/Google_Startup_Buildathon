"""Automated verification suite for Keepwell Part B mocks.

Covers:
1. Fixture generation from real simulation dataset (9 centres, 20 cases, all 5 PaymentIntent states, Debrief with unresolved part)
2. Every Contract Section 5 REST endpoint, cursor pagination, error shape, X-Mock-Fail: 503, and stateful mutations
3. Contract Section 7 WebSocket Live Call protocol (C03 replay mode + Echo mode)
4. Firestore emulator seeder & C03 time-lapse dry-run serialization
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from mocks.fixtures.build_fixtures import OUT_DIR, build_all
from mocks.firestore.seed_emulator import seed_all, to_firestore_value
from mocks.firestore.timelapse_c03 import run_timelapse
from mocks.rest.server import app as rest_app, store
from mocks.ws.server import app as ws_app


@pytest.fixture(autouse=True)
def reset_store():
    store.reset()
    yield


def test_fixtures_built_from_real_dataset():
    summary = build_all()
    assert summary["centres"] == 9
    assert summary["demo_cases"] == 20
    assert summary["tickets"] == 20
    assert summary["technicians"] >= 30
    assert summary["safefix"] >= 10

    payments = json.loads((OUT_DIR / "payments.json").read_text(encoding="utf-8"))
    states = {p["status"] for p in payments}
    assert {"created", "pending", "paid", "failed", "expired"}.issubset(states)

    tickets = json.loads((OUT_DIR / "tickets.json").read_text(encoding="utf-8"))
    c03 = next(t for t in tickets if t["case_id"] == "C03")
    assert c03["debrief"] is not None
    assert len(c03["debrief"]["unresolved"]) >= 1
    assert c03["card"]["household"]["display_name"] == "Sunita Sharma"


def test_health_meta_and_openapi():
    client = TestClient(rest_app)
    assert client.get("/healthz").status_code == 200
    assert client.get("/readyz").status_code == 200
    v = client.get("/v1/meta/version")
    assert v.status_code == 200
    assert v.json()["contract_version"] == "v1"
    oa = client.get("/openapi.json")
    assert oa.status_code == 200
    assert "/v1/tickets" in oa.json()["paths"]


def test_error_injection_and_error_shape():
    client = TestClient(rest_app)
    r = client.get("/v1/tickets", headers={"X-Mock-Fail": "503"})
    assert r.status_code == 503
    body = r.json()
    assert "error" in body
    assert set(body["error"].keys()) == {"code", "message", "field", "request_id"}

    nf = client.get("/v1/tickets/does-not-exist")
    assert nf.status_code == 404
    assert nf.json()["error"]["code"] == "ticket_not_found"


def test_centre_console_endpoints_and_mutations():
    client = TestClient(rest_app)

    # List tickets ordered safety -> urgent -> standard -> planned + pagination
    r = client.get("/v1/tickets?limit=5")
    assert r.status_code == 200
    data = r.json()
    assert len(data["items"]) == 5
    assert data["next_cursor"] == "5"
    assert data["items"][0]["urgency_class"] == "safety"

    # Fetch C03 detail
    cases = client.get("/v1/admin/demo/cases").json()["items"]
    c03_case = next(c for c in cases if c["case_id"] == "C03")
    tid = c03_case["ticket_id"]

    detail = client.get(f"/v1/tickets/{tid}")
    assert detail.status_code == 200
    d = detail.json()
    assert d["card"]["id"] == tid
    assert len(d["candidates"]) == 3
    assert "fix_confidence" in d["candidates"][0]["score_breakdown"]

    # Reclassify urgency
    rec = client.post(
        f"/v1/tickets/{tid}/reclassify-urgency",
        json={"class": "urgent", "reason": "Customer needs washer before school week"},
    )
    assert rec.status_code == 200
    assert rec.json()["card"]["urgency_class"] == "urgent"
    assert rec.json()["urgency"][-1]["assessed_by"] == "centre_console"

    # Reassign technician
    alt_tech_id = d["candidates"][1]["technician_id"]
    reas = client.post(
        f"/v1/tickets/{tid}/reassign",
        json={
            "technician_id": alt_tech_id,
            "slot_start": "2026-11-21T16:00:00+05:30",
            "slot_end": "2026-11-21T18:00:00+05:30",
            "reason": "Earlier job overran",
        },
    )
    assert reas.status_code == 200
    assert reas.json()["visit"]["technician_id"] == alt_tech_id

    # Overrides list captured both mutations
    ov = client.get("/v1/centre/overrides").json()["items"]
    assert len(ov) >= 2

    # Rerun diagnosis
    rr = client.post(f"/v1/tickets/{tid}/rerun-diagnosis")
    assert rr.status_code == 200
    assert rr.json()["diagnosis"]["rerun_of"] is not None

    # Message household
    msg = client.post(f"/v1/tickets/{tid}/message", json={"text": "Technician arriving at 4 PM"})
    assert msg.status_code == 200
    assert msg.json()["actor"] == "centre"

    # Return to brand
    rtb = client.post(f"/v1/tickets/{tid}/return-to-brand", json={"reason": "Out of authority"})
    assert rtb.status_code == 200
    assert rtb.json()["card"]["status"] == "returned_to_brand"

    # Overview, technicians, calendar, stock, prices, appliance timeline, safefix
    assert "fvr_14d" in client.get("/v1/centre/overview?centre_key=c_fw").json()
    assert len(client.get("/v1/centre/technicians?centre_key=c_fw").json()["items"]) >= 2
    assert "items" in client.get("/v1/centre/calendar?centre_key=c_fw").json()
    assert "items" in client.get("/v1/centre/stock?centre_key=c_fw").json()
    assert "items" in client.get("/v1/centre/prices?centre_key=c_fw").json()

    app_id = d["card"]["appliance"]["id"]
    assert "items" in client.get(f"/v1/appliances/{app_id}/timeline").json()
    sf = client.get("/v1/safefix").json()["items"]
    assert len(sf) >= 10
    assert client.get(f"/v1/safefix/{sf[0]['code']}").status_code == 200


def test_technician_parts_brand_public_channels_and_demo():
    client = TestClient(rest_app)
    cases = client.get("/v1/admin/demo/cases").json()["items"]
    c03_tid = next(c for c in cases if c["case_id"] == "C03")["ticket_id"]
    c03 = client.get(f"/v1/tickets/{c03_tid}").json()
    visit_id = c03["visit"]["id"]

    # Technician endpoints
    assert len(client.get("/v1/technicians/me/jobs").json()["items"]) >= 1
    assert client.get(f"/v1/visits/{visit_id}").status_code == 200
    assert client.post(f"/v1/visits/{visit_id}/check-in", json={"lat": 17.48, "lon": 78.39}).status_code == 200
    assert client.post(f"/v1/visits/{visit_id}/parts-used", json={"parts": [{"part_no": "WC-WM-DPUMP", "quantity": 1}]}).status_code == 200
    assert client.post(f"/v1/visits/{visit_id}/media/upload-url", json={"filename": "note.ogg"}).status_code == 200
    assert client.post(f"/v1/technicians/me/location", json={"lat": 17.48, "lon": 78.39, "at": "2026-11-21T14:05:00+05:30"}).status_code == 200

    # Firm quote
    q = client.post(
        f"/v1/tickets/{c03_tid}/quotes",
        json={"lines": [{"kind": "visit_fee", "description": "Visit", "amount_paise": 45000, "payer": "household"}]},
    )
    assert q.status_code == 200
    assert q.json()["quote_type"] == "firm"

    # Debrief + confirm
    deb = client.post(f"/v1/visits/{visit_id}/debrief", json={"media_ref": "gs://mock/note.ogg", "language": "hi"})
    assert deb.status_code == 200
    assert len(deb.json()["unresolved"]) >= 1
    conf = client.post(f"/v1/visits/{visit_id}/debrief/confirm", json={"extracted": deb.json()["extracted"]})
    assert conf.status_code == 200
    assert conf.json()["status"] == "confirmed"

    # Outcome + OTP close
    assert client.post(f"/v1/visits/{visit_id}/outcome", json={"outcome": "fixed", "notes": "Pump replaced"}).status_code == 200
    otp = client.post(f"/v1/visits/{visit_id}/close/request-otp").json()
    closed = client.post(f"/v1/visits/{visit_id}/close/confirm", json={"otp_ref": otp["otp_ref"], "code": otp["sandbox_code"]})
    assert closed.status_code == 200
    assert closed.json()["status"] == "closed"

    # Parts centre lifecycle
    prs = client.get("/v1/partscentre/requests").json()["items"]
    assert len(prs) >= 1
    pr_id = prs[0]["id"]
    assert client.post(f"/v1/partscentre/requests/{pr_id}/accept").json()["status"] == "accepted"
    assert client.post(f"/v1/partscentre/requests/{pr_id}/ready").json()["status"] == "ready"
    assert client.post(f"/v1/partscentre/requests/{pr_id}/handover").json()["status"] == "handed_over"
    assert client.put("/v1/partscentre/stock", json={"part_no": "WC-WM-DPUMP", "quantity": 7}).status_code == 200

    # Brand & retailer
    assert len(client.get("/v1/brand/requests").json()["items"]) >= 3
    assert "fvr_14d" in client.get("/v1/brand/analytics").json()
    br = client.post(
        "/v1/channels/brand/requests",
        headers={"X-Keepwell-Key": "demo-brand-key"},
        json={"brand": "aerovane", "centre_key": "c_cc", "claimed_warranty": "in_warranty", "complaint": "Weak cooling"},
    )
    assert br.status_code == 202
    assert br.json()["status"] == "declined"
    rh = client.post(
        "/v1/channels/retailer/handovers",
        headers={"X-Keepwell-Key": "demo-retailer-key"},
        json={"retailer": "Digital Plaza Electronics", "requested_job": "installation"},
    )
    assert rh.status_code == 202
    assert rh.json()["status"] == "received"

    # Household public magic token flow
    demo_hhs = client.get("/v1/admin/demo/households?centre_key=c_fw").json()["items"]
    token = demo_hhs[0]["magic_token"]
    assert client.post("/v1/public/session", json={"magic_token": token}).status_code == 200
    assert client.get(f"/v1/public/home/{token}").status_code == 200
    assert client.get(f"/v1/public/quotes/{token}").status_code == 200
    assert client.post(f"/v1/public/quotes/{token}/approve").status_code == 200
    pi = client.post(f"/v1/public/quotes/{token}/pay-intent", json={"method": "google_pay"}).json()
    assert pi["status"] == "pending"
    assert client.get(f"/v1/public/quotes/{token}/payment").json()["id"] == pi["id"]
    paid = client.post(
        f"/v1/public/quotes/{token}/payment/sandbox-complete",
        json={"payment_id": pi["id"], "result": "success"},
    ).json()
    assert paid["status"] == "paid"
    assert client.post(f"/v1/public/otp/{token}/confirm", json={"code": "482910"}).status_code == 200

    # WhatsApp simulator
    wa = client.post(
        "/v1/channels/whatsapp/simulator/inbound",
        json={
            "to_number": "+91 59885 77764",
            "from_phone": "+91 50971 16577",
            "sender_profile_name": "Sunita Sharma",
            "messages": [{"type": "text", "text": {"body": "There is smoke coming from the motor"}}],
        },
    )
    assert wa.status_code == 200
    assert wa.json()["safety_flag"] is True

    # Demo play-case & reset
    assert client.post("/v1/admin/demo/play-case", json={"case_id": "C03"}).status_code == 200
    assert client.post("/v1/admin/projection/rebuild").status_code == 200
    assert client.post("/v1/admin/demo/reset").status_code == 200


def test_ws_c03_replay_and_echo_mode(monkeypatch):
    monkeypatch.setenv("MOCK_WS_DELAY_S", "0.005")
    client = TestClient(ws_app)

    # 1. C03 replay mode
    seen_types: set[str] = set()
    seen_ui_hints: set[str] = set()
    binary_chunks = 0
    with client.websocket_connect("/v1/live/call?token=demo") as ws:
        ws.send_json({
            "type": "start",
            "centre_key": "c_fw",
            "caller_number": "+91 50971 16577",
            "language_hint": None,
            "resume_conversation_id": None,
        })
        while True:
            msg = ws.receive()
            if msg.get("bytes") is not None:
                binary_chunks += 1
            elif msg.get("text") is not None:
                data = json.loads(msg["text"])
                seen_types.add(data["type"])
                if data["type"] == "ui_hint":
                    seen_ui_hints.add(data["kind"])
                if data["type"] == "ended":
                    break

    assert {"ready", "transcript", "video_link", "modality", "ui_hint", "event", "go_away", "ended"}.issubset(seen_types)
    assert {"show_sticker", "show_display", "show_drain_filter", "hold_steady"}.issubset(seen_ui_hints)
    assert binary_chunks >= 2

    # 2. Echo mode
    with client.websocket_connect("/v1/live/call?token=demo") as ws:
        ws.send_json({
            "type": "start",
            "centre_key": "c_fw",
            "caller_number": "+91 50971 16577",
            "language_hint": "echo",
            "resume_conversation_id": None,
        })
        ready = ws.receive_json()
        assert ready["type"] == "ready"
        ws.send_json({"type": "client_state", "modality": "video", "muted": False})
        assert ws.receive_json()["type"] == "modality"
        assert ws.receive_json()["type"] == "ui_hint"
        ws.send_json({"type": "end"})
        assert ws.receive_json()["type"] == "ended"


def test_firestore_seeder_and_timelapse_dry_run():
    assert "geoPointValue" in to_firestore_value({"lat": 17.44, "lon": 78.34})
    assert "timestampValue" in to_firestore_value("2026-11-21T08:15:00+05:30")

    seed_res = seed_all(dry_run=True)
    assert seed_res["centres"] == 9
    assert seed_res["tickets"] == 20
    assert seed_res["c03_snapshots"] == 5

    tl_res = run_timelapse(delay=0.0, dry_run=True)
    assert tl_res["events_emitted"] >= 25
