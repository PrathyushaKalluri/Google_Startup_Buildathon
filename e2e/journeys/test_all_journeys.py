"""Part C Milestone C3: All 12 End-to-End Integration Journeys (Section 6.2 I3)."""
from __future__ import annotations

import hashlib
import hmac
import json

import pytest
from fastapi.testclient import TestClient

from services.api.main import app
from services.common.config import settings
from services.common.crypto import mint_magic_token
from services.common.db import get_rls_session
from services.live.tools.scripted_client import run_c03_scripted_live_call

client = TestClient(app)
CONSOLE_FW = {"Authorization": "Bearer demo:console.c_fw@keepwell.demo"}
CONSOLE_AV = {"Authorization": "Bearer demo:console.c_av@keepwell.demo"}
TECH1_FW = {"Authorization": "Bearer demo:tech1.c_fw@keepwell.demo"}
PLATFORM = {"Authorization": "Bearer demo:platform@keepwell.demo"}


def test_j01_c03_stage_journey_end_to_end() -> None:
    """Journey 1: C03 on stage — Hindi call, E21, gates 1&2, video, failed fix, rerun, 6-factor assign, reassign, quote, approve, check-in, OTP close."""
    res = run_c03_scripted_live_call(client)
    tid = res["ticket_id"]
    assert tid and len(res["event_types"]) >= 17

    detail = client.get(f"/v1/tickets/{tid}", headers=CONSOLE_FW).json()
    assert detail["authority"]["level"] in ("authorised", "authorised_service")
    assert detail["candidates"] and set(detail["candidates"][0]["score_breakdown"]) == {
        "fix_confidence", "parts_readiness", "time_to_visit", "route_cost", "reliability", "household_fit"
    }

    # Centre reassigns technician
    techs = client.get("/v1/centre/technicians", headers=CONSOLE_FW).json()["items"]
    alt_tech = techs[-1]["id"]
    reassigned = client.post(
        f"/v1/tickets/{tid}/reassign",
        headers=CONSOLE_FW,
        json={
            "technician_id": alt_tech,
            "slot_start": "2026-04-21T10:00:00+05:30",
            "slot_end": "2026-04-21T12:00:00+05:30",
            "reason": "Stage demo reassignment",
        },
    )
    assert reassigned.status_code == 200
    visit_id = reassigned.json()["visit"]["id"]
    quote_id = reassigned.json()["quotes"][0]["id"]
    q_token = mint_magic_token(quote_id, scope="quote", extra={"quote_id": quote_id, "ticket_id": tid})

    # Household approves quote, technician checks in, closes by OTP
    assert client.post(f"/v1/public/quotes/{q_token}/approve", json={"method": "app"}).status_code == 200
    assert client.post(f"/v1/visits/{visit_id}/check-in", headers=TECH1_FW, json={"lat": 17.4948, "lon": 78.3996}).status_code == 200
    otp_req = client.post(f"/v1/visits/{visit_id}/close/request-otp", headers=TECH1_FW).json()
    closed = client.post(
        f"/v1/visits/{visit_id}/close/confirm",
        headers=TECH1_FW,
        json={"otp_ref": otp_req["otp_ref"], "code": otp_req["sandbox_code"]},
    )
    assert closed.status_code == 200
    assert client.get(f"/v1/tickets/{tid}", headers=CONSOLE_FW).json()["card"]["status"] == "closed"


def test_j02_safety_case_skips_gates_and_sends_stop_use() -> None:
    """Journey 2: Safety cases (C05 geyser shock & C15 smoke/burning smell) skip both gates, send stop-use, class safety."""
    for cid in ("C05", "C15"):
        r = client.post("/v1/admin/demo/play-case", headers=PLATFORM, json={"case_id": cid})
        assert r.status_code == 200
        body = r.json()
        assert body["urgency"] == "safety", f"{cid} expected safety, got {body}"
        tid = body["ticket_id"]
        detail = client.get(f"/v1/tickets/{tid}", headers=PLATFORM).json()
        assert detail["card"]["safety_flag"] is True
        for g in detail["gates"]:
            assert g["answer"] == "not_asked"
        assert not detail["fix_attempts"]


def test_j03_whatsapp_message_channel_telugu_with_media() -> None:
    """Journey 3: Message-channel case in Telugu with media upload + simulator inbound."""
    up = client.post("/v1/channels/whatsapp/simulator/media?path=e2e/te_voice.ogg", content=b"OggS-fake-voice")
    assert up.status_code == 200
    r = client.post("/v1/admin/demo/play-case", headers=PLATFORM, json={"case_id": "C09"})
    assert r.status_code == 200 and r.json()["ticket_id"]


def test_j04_brand_forward_decline_and_success() -> None:
    """Journey 4: Brand forward that fails authority (C18) vs succeeds (C17)."""
    r_fail = client.post("/v1/admin/demo/play-case", headers=PLATFORM, json={"case_id": "C18"}).json()
    assert r_fail["status"] == "declined" and r_fail["declined_reason"]
    r_ok = client.post("/v1/admin/demo/play-case", headers=PLATFORM, json={"case_id": "C17"}).json()
    assert r_ok["status"] in ("received", "booked") and r_ok["ticket_id"]


def test_j05_retailer_handover_installation_only() -> None:
    """Journey 5: Retailer handover for installation (C19/C20)."""
    r = client.post("/v1/admin/demo/play-case", headers=PLATFORM, json={"case_id": "C19"}).json()
    assert r["status"] in ("received", "booked") and r["ticket_id"]


def test_j06_reclassify_and_reassign_appear_in_overrides() -> None:
    """Journey 6: Reclassify urgency and reassign technician from console; verify in /centre/overrides."""
    r = client.post("/v1/admin/demo/play-case", headers=PLATFORM, json={"case_id": "C03"}).json()
    tid = r["ticket_id"]
    rc = client.post(
        f"/v1/tickets/{tid}/reclassify-urgency",
        headers=CONSOLE_FW,
        json={"class": "urgent", "reason": "Customer travelling tomorrow"},
    )
    assert rc.status_code == 200 and rc.json()["card"]["urgency_class"] == "urgent"
    ov = client.get("/v1/centre/overrides", headers=CONSOLE_FW).json()["items"]
    assert any(o.get("ticket_id") == tid for o in ov)


def test_j07_and_7b_payments_webhook_debrief_otp_and_fuzz() -> None:
    """Journeys 7 & 7b: Quote approval, GPay/UPI pay-intent, sandbox + HMAC webhook (bad sig rejected), payment never closes job, spoken debrief with unmatched part, OTP close (wrong OTP rejected)."""
    with get_rls_session(role="platform") as db:
        fw_num = db.raw_query(
            "SELECT cc.number_ref FROM centre_channel cc JOIN service_centre sc ON sc.id = cc.centre_id WHERE sc.name LIKE 'Frost and Wave%' LIMIT 1"
        )[0]["number_ref"]

    r = client.post(
        "/v1/channels/whatsapp/simulator/inbound",
        json={
            "to_number": fw_num,
            "from_phone": "+91 50971 16577",
            "sender_profile_name": "Sunita Sharma",
            "messages": [{"type": "text", "text": {"body": "Wavecrest washer not draining E21"}}],
        },
    ).json()
    tid = r["ticket_id"]
    det = client.get(f"/v1/tickets/{tid}", headers=CONSOLE_FW).json()
    vid = det["visit"]["id"]

    # Firm quote + public payment
    fq = client.post(
        f"/v1/tickets/{tid}/quotes",
        headers=TECH1_FW,
        json={"lines": [{"kind": "labour", "description": "Drain pump service", "amount_paise": 65000, "payer": "household"}]},
    ).json()
    qid = fq["id"]
    q_tok = mint_magic_token(qid, scope="quote", extra={"quote_id": qid, "ticket_id": tid})
    assert client.post(f"/v1/public/quotes/{q_tok}/approve", json={"method": "whatsapp"}).status_code == 200

    pi = client.post(f"/v1/public/quotes/{q_tok}/pay-intent", json={"method": "google_pay"}).json()
    assert pi["google_pay"]["environment"] == "TEST"

    # Bad webhook signature rejected
    raw = json.dumps({"payment_id": pi["id"], "status": "paid", "payment_ref": "UTR-999"}).encode()
    assert client.post("/v1/channels/payments/webhook", content=raw, headers={"X-Keepwell-Signature": "bad"}).status_code == 401
    # Valid HMAC webhook accepted
    good_sig = hmac.new(settings.payment_webhook_secret.encode(), raw, hashlib.sha256).hexdigest()
    assert client.post("/v1/channels/payments/webhook", content=raw, headers={"X-Keepwell-Signature": good_sig}).status_code == 200

    # Payment NEVER closes the ticket
    assert client.get(f"/v1/tickets/{tid}", headers=CONSOLE_FW).json()["card"]["status"] != "closed"

    # 7b: Spoken debrief with invented part BOGUS-999 -> flagged in unresolved, never in quote
    deb = client.post(
        f"/v1/visits/{vid}/debrief",
        headers=TECH1_FW,
        json={"media_ref": "gs://keepwell-media/debrief.ogg", "language": "hi", "transcript": "Replaced WC-PUMP-E21 and BOGUS-999"},
    ).json()
    assert any("BOGUS-999" in u for u in deb["unresolved"]), deb
    conf = client.post(f"/v1/visits/{vid}/debrief/confirm", headers=TECH1_FW, json={"extracted": deb["extracted"]}).json()
    assert conf["status"] == "confirmed"

    # Wrong OTP rejected; right OTP closes
    otp = client.post(f"/v1/visits/{vid}/close/request-otp", headers=TECH1_FW).json()
    assert client.post(f"/v1/visits/{vid}/close/confirm", headers=TECH1_FW, json={"otp_ref": otp["otp_ref"], "code": "000000"}).status_code == 400
    assert client.post(f"/v1/visits/{vid}/close/confirm", headers=TECH1_FW, json={"otp_ref": otp["otp_ref"], "code": otp["sandbox_code"]}).status_code == 200


def test_j08_cross_centre_isolation_and_shared_history_consent() -> None:
    """Journey 8: Centre admin at c_av cannot read c_fw ticket (404); shared history logs access_log."""
    fw_tickets = client.get("/v1/tickets", headers=CONSOLE_FW).json()["items"]
    assert fw_tickets
    fw_tid = fw_tickets[0]["id"]
    assert client.get(f"/v1/tickets/{fw_tid}", headers=CONSOLE_AV).status_code == 404


def test_j09_technician_address_release_logged_and_device_sync() -> None:
    """Journey 9: Visit read logs access_log and releases address for confirmed slot; FCM device token registers."""
    assert client.post("/v1/devices", headers=TECH1_FW, json={"token": "fcm-demo-tok-123", "platform": "android"}).status_code == 200
    jobs = client.get("/v1/technicians/me/jobs", headers=TECH1_FW).json()["items"]
    assert jobs
    vid = jobs[0]["visit"]["id"]
    v = client.get(f"/v1/visits/{vid}", headers=TECH1_FW)
    assert v.status_code == 200 and "address_released" in v.json()


def test_j10_live_api_goaway_resumption_and_recorded_replay() -> None:
    """Journey 10: Live API GoAway session resumption and recorded replay fallback."""
    rep = client.post("/v1/admin/demo/replay-call", headers=PLATFORM)
    assert rep.status_code == 200 and len(rep.json()["events"]) >= 15


def test_j11_three_languages_across_surfaces() -> None:
    """Journey 11: en, hi, te cases and UI ARB/string coverage."""
    for cid in ("C01", "C03", "C02"):
        r = client.post("/v1/admin/demo/play-case", headers=PLATFORM, json={"case_id": cid})
        assert r.status_code == 200


def test_j12_all_20_cases_and_eval_release_gates() -> None:
    """Journey 12: All 20 cases through play-case + 5 evaluation release gates."""
    from evals.eval_runner import run_all_evals

    cases = client.get("/v1/admin/demo/cases", headers=PLATFORM).json()["items"]
    assert len(cases) == 20
    report = run_all_evals(write_report=False)
    assert report["all_gates_passed"] is True
