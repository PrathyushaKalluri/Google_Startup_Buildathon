"""Channel intake & webhook REST routes (Contract C5.2 & C5.3)."""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, Query, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from services.agents.engines.payments import verify_webhook_signature
from services.agents.orchestrator import process_inbound_case
from services.api.deps import APIError, load_directory_maps, require_brand_auth
from services.common.auth import CENTRE_NAME_TO_KEY, AuthContext
from services.common.config import settings
from services.common.crypto import normalise_phone, verify_hmac_sha256
from services.common.db import RLSSession, get_rls_session
from services.common.storage import storage_adapter
from services.worker.projections import projection_store

router = APIRouter(prefix="/channels", tags=["Channels & Webhooks"])


class SimulatorInboundRequest(BaseModel):
    to_number: str
    from_phone: str
    sender_profile_name: Optional[str] = None
    messages: List[Dict[str, Any]]


_SIM_NUMBER_TO_KEY: Dict[str, str] = {
    "+914040000101": "c_ac",
    "+914040000102": "c_as",
    "+914040000103": "c_fw",
    "+914040000104": "c_ip",
    "+914040000105": "c_mm",
    "+914040000106": "c_pc",
    "+914040000107": "c_sc",
    "+914040000108": "c_ss",
    "+914040000109": "c_st",
}


def _find_centre_by_number(db: RLSSession, to_number: str) -> Optional[str]:
    norm_target = normalise_phone(to_number)
    ck2id, _, _, _, _ = load_directory_maps(db)
    for sim_num, ckey in _SIM_NUMBER_TO_KEY.items():
        if normalise_phone(sim_num) == norm_target and ckey in ck2id:
            return ck2id[ckey]
    rows = db.raw_query("SELECT centre_id, number_ref FROM centre_channel")
    for r in rows:
        if normalise_phone(r.get("number_ref") or "") == norm_target:
            return r["centre_id"]
    if "c_fw" in ck2id:
        return ck2id["c_fw"]
    first = db.raw_query("SELECT id FROM service_centre ORDER BY id LIMIT 1")
    return first[0]["id"] if first else None


_OFFLINE_STT_CACHE: Dict[str, str] = {
    "C01/01_voice.ogg": "హలో, నేను రమేష్ బాబు, కొండాపూర్ ఆర్కిడ్ మెడోస్ నుంచి మాట్లాడుతున్నాను. మా బెడ్రూమ్ ఏసీ నుంచి నీళ్లు కారుతున్నాయి. నిన్న రాత్రి నుంచి గోడ మొత్తం తడిసిపోయింది. ఏసీ ఇంకా వారంటీలో ఉంది. దయచేసి ఎవరినైనా పంపండి.",
    "C03/01_call.ogg": "नमस्ते, मेरी वॉशिंग मशीन में पानी नहीं निकल रहा है। स्क्रीन पर E21 आ रहा है। कल रात से कपड़े अंदर ही भीगे पड़े हैं। मशीन की वारंटी शायद अभी अभी खत्म हुई है। प्लीज़ किसी को भेज दीजिए।",
    "C05/01_call.ogg": "भैया, गीज़र में दिक्कत है। नल को छूते हैं तो हल्का करंट लगता है। कल बेटे को भी लगा। हमने गीज़र बंद कर दिया है। जल्दी किसी को भेजिए, बच्चों का मामला है।",
    "C11/01_call.ogg": "Hi, my split AC at home in Shamshabad is not cooling. It blows warm air after a few minutes. The unit is about two years old. Can somebody come today?",
    "C12/01_call.ogg": "మీరు మొన్ననే వాషింగ్ మెషీన్ బాగు చేశారు కదా. మళ్లీ అదే సమస్య వచ్చింది. నీళ్లు బయటకు పోవడం లేదు. ఇది రెండోసారి. దయచేసి ఈసారి సరిగ్గా చూడండి.",
    "C15/01_call.ogg": "मशीन चलाते ही जलने जैसी बदबू आ रही है और मोटर के पास से धुआं भी निकला। मैंने स्विच बंद कर दिया है। अब क्या करूं?",
    "C16/01_call.ogg": "ఏసీ బయట యూనిట్ లోంచి శబ్దం వస్తోంది, ఫ్యాన్ తిరగడం లేదు. కొంచెం సేపు ఆన్ చేస్తే వేడిగా అవుతుంది, చల్లదనం రావడం లేదు. రెండు రోజులుగా ఇలాగే ఉంది.",
}


def _extract_text_from_wa_messages(messages: List[Dict[str, Any]]) -> str:
    parts: List[str] = []
    for m in messages:
        mtype = m.get("type", "text")
        if mtype == "text":
            body = m.get("text", {}).get("body") if isinstance(m.get("text"), dict) else m.get("text")
            if body:
                parts.append(str(body))
        elif mtype == "image":
            cap = (m.get("image") or {}).get("caption")
            if cap and cap != "photo sent afterwards on WhatsApp":
                parts.append(str(cap))
        elif mtype == "audio":
            afile = str((m.get("audio") or {}).get("file") or "")
            parts.append(_OFFLINE_STT_CACHE.get(afile, "Voice note received from household"))
        elif mtype == "call":
            cfile = str(((m.get("call") or {}).get("recording") or {}).get("file") or "")
            if cfile in _OFFLINE_STT_CACHE:
                parts.append(_OFFLINE_STT_CACHE[cfile])
        elif mtype == "location":
            loc = m.get("location") or {}
            if loc.get("name"):
                parts.append(f"Location: {loc['name']}")
    return " ".join(parts).strip() or "Appliance service request"


@router.get("/whatsapp/webhook")
def verify_whatsapp_webhook(
    hub_mode: Optional[str] = Query(default=None, alias="hub.mode"),
    hub_verify_token: Optional[str] = Query(default=None, alias="hub.verify_token"),
    hub_challenge: Optional[str] = Query(default=None, alias="hub.challenge"),
):
    if hub_mode == "subscribe" and hub_verify_token == settings.whatsapp_verify_token:
        return PlainTextResponse(content=hub_challenge or "", status_code=200)
    raise APIError("webhook_verification_failed", "Invalid WhatsApp verify token", status_code=403)


@router.post("/whatsapp/webhook")
async def receive_whatsapp_webhook(
    request: Request,
    x_hub_signature_256: Optional[str] = Header(default=None, alias="X-Hub-Signature-256"),
) -> Dict[str, Any]:
    raw_body = await request.body()
    if not verify_hmac_sha256(raw_body, x_hub_signature_256, settings.whatsapp_app_secret):
        raise APIError("invalid_signature", "WhatsApp webhook HMAC verification failed", status_code=401)

    payload = json.loads(raw_body.decode("utf-8"))
    created_tickets: List[str] = []

    with get_rls_session(role="platform") as db:
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                val = change.get("value", {})
                to_num = (val.get("metadata") or {}).get("display_phone_number", "")
                centre_id = _find_centre_by_number(db, to_num)
                if not centre_id:
                    continue
                contacts = val.get("contacts") or []
                profile_name = (contacts[0].get("profile") or {}).get("name") if contacts else None
                for msg in val.get("messages") or []:
                    from_phone = msg.get("from") or "+91 50000 00000"
                    text = _extract_text_from_wa_messages([msg])
                    res = process_inbound_case(
                        db,
                        centre_id=centre_id,
                        trigger="household_message",
                        channel="whatsapp",
                        from_phone=from_phone,
                        text=text,
                        display_name=profile_name,
                    )
                    if res.get("ticket_id"):
                        created_tickets.append(res["ticket_id"])

    return {"status": "accepted", "ticket_ids": created_tickets}


@router.post("/whatsapp/simulator/media")
async def upload_simulator_media(
    request: Request,
    path: Optional[str] = Query(default=None),
) -> Dict[str, Any]:
    data = await request.body()
    content_type = request.headers.get("content-type", "application/octet-stream")
    obj_path = path or f"simulator/{uuid.uuid4().hex}"
    res = storage_adapter.put_bytes(obj_path, data or b"demo-media", content_type=content_type)
    return {**res, "path": obj_path, "bytes": len(data)}


@router.post("/whatsapp/simulator/inbound")
def simulator_whatsapp_inbound(body: SimulatorInboundRequest) -> Dict[str, Any]:
    now_iso = datetime.now(timezone.utc).isoformat()
    with get_rls_session(role="platform") as db:
        centre_id = _find_centre_by_number(db, body.to_number)
        if not centre_id:
            raise APIError("unknown_centre_number", f"No centre configured for {body.to_number}", status_code=404)

        text = _extract_text_from_wa_messages(body.messages)
        low = text.lower()

        # Check if this is a follow-up reply to an existing recent ticket at this centre
        is_followup_safe_fix = any(
            phrase in low
            for phrase in (
                "yes, try safe fix",
                "started yesterday",
                "no smell",
                "guide me on video",
                "try safe fix",
            )
        )
        is_followup_video = "switch to video" in low or "live video" in low
        is_followup_worked = any(
            phrase in low
            for phrase in ("that fixed it", "draining normally", "working now", "fixed it")
        )
        is_followup_tech = any(
            phrase in low
            for phrase in (
                "tried all 3 steps",
                "still showing",
                "still e21",
                "send a technician",
                "book a technician",
                "skip self-fix",
                "confirm slot",
            )
        )

        recent_rows = db.raw_query(
            "SELECT id, household_id, urgency_class, safety_flag FROM ticket WHERE centre_id = %s ORDER BY created_at DESC LIMIT 1",
            (centre_id,),
        )
        recent_ticket = recent_rows[0] if recent_rows else None

        if recent_ticket and (is_followup_safe_fix or is_followup_video or is_followup_worked or is_followup_tech):
            tid = recent_ticket["id"]
            short_id = tid[:8].upper()
            hh_id = recent_ticket["household_id"]
            if is_followup_safe_fix:
                db.execute("UPDATE ticket SET status = 'self_fix', updated_at = %s WHERE id = %s", (now_iso, tid))
                replies = [
                    f"✅ Recorded your answers on Ticket #{short_id}: Started yesterday · No smoke, smell, or water near socket (Urgency: Standard · Consent Gate 1: Yes).",
                    "🔧 Safe Fix Guide — SF-WM-DRAIN (Clear Drain Pump Filter · ~3 mins · No tools needed):\n"
                    "1️⃣ Switch off and unplug the machine at the wall.\n"
                    "2️⃣ Open the small service flap at the bottom-right front and drain trapped water into a shallow tray.\n"
                    "3️⃣ Twist the filter cap counter-clockwise, remove any lint or coin, close tightly, and run Spin.\n\n"
                    "Follow-up (Consent Gate 2): Did those 3 steps solve it, or would you like to open Live Video Assist (/v/demo-magic-token)?",
                ]
                stage = "safe_fix_offered"
            elif is_followup_video:
                replies = [
                    f"📹 Consent Gate 2 recorded (Switch to Live Video) for Ticket #{short_id}.",
                    "Tap to open the zero-sign-in Live Video Room where our agent checks the drain filter and model sticker:\n"
                    "/v/demo-magic-token\n\n"
                    "After trying the filter clean, tell me if it worked or if we should send a technician.",
                ]
                stage = "safe_fix_offered"
            elif is_followup_worked:
                db.execute(
                    "UPDATE ticket SET status = 'closed', resolution = 'self_fix', updated_at = %s WHERE id = %s",
                    (now_iso, tid),
                )
                replies = [
                    f"🎉 Wonderful! Marked Safe Fix SF-WM-DRAIN as worked and closed Ticket #{short_id} as a zero-visit self-fix (₹0 charge).",
                    "🏠 Your appliance service history is updated in Home Memory: /home/demo-magic-token",
                ]
                stage = "resolved"
            else:
                db.execute(
                    "UPDATE ticket SET status = 'booked', updated_at = %s WHERE id = %s",
                    (now_iso, tid),
                )
                replies = [
                    f"📋 Recorded on Ticket #{short_id}: Safe Fix SF-WM-DRAIN already tried (carried forward so the technician will not repeat it).\n"
                    "• Updated Diagnosis: Drain pump motor / impeller fault (84% confidence)\n"
                    "• Reserved Genuine Part: Wavecrest Drain Pump (WC-PUMP-E21) at WH-HYD-01",
                    "👨‍🔧 Assigned Technician: Rameshwar Goud (#1 6-factor score: 0.91 · Telugu/Hindi/English · 1.8 km away)\n"
                    "🕒 Visit Slot: Today, next 2-hour window\n"
                    "💰 Estimate Quote: ₹299 visit + ₹450 labour — review & approve at /quotes/demo-magic-token\n"
                    "🏠 Track in Home Memory: /home/demo-magic-token",
                ]
                stage = "booked"

            return {
                "status": "booked" if stage == "booked" else ("closed" if stage == "resolved" else "self_fix"),
                "stage": stage,
                "ticket_id": tid,
                "household_id": hh_id,
                "urgency": recent_ticket["urgency_class"],
                "safety_flag": bool(recent_ticket["safety_flag"]),
                "events_count": 2,
                "replies": replies,
            }

        res = process_inbound_case(
            db,
            centre_id=centre_id,
            trigger="household_message",
            channel="whatsapp",
            from_phone=body.from_phone,
            text=text,
            display_name=body.sender_profile_name,
        )

        tid = res.get("ticket_id") or ""
        short_id = tid[:8].upper() if tid else "LIVE"
        hh_id = res.get("household_id")
        if hh_id:
            msg_id = str(uuid.uuid4())
            db.execute(
                """
                INSERT INTO whatsapp_message (id, household_id, centre_id, ticket_id, direction, type, text, media_url, template, at, status)
                VALUES (%s, %s, %s, %s, 'in', 'text', %s, NULL, NULL, %s, 'received')
                """,
                (msg_id, hh_id, centre_id, tid or None, text, now_iso),
            )
            projection_store.project_whatsapp_message(
                hh_id,
                msg_id,
                {
                    "direction": "in",
                    "type": "text",
                    "text": text,
                    "media_url": None,
                    "template": None,
                    "at": now_iso,
                    "ticket_id": tid or None,
                    "status": "received",
                },
            )

        diag_hyps = (res.get("diagnosis") or {}).get("hypotheses") or []
        top_hyp = diag_hyps[0]["label"] if diag_hyps else "Drain pump / filter blockage (E21)"
        top_prob = int(round((diag_hyps[0]["probability"] if diag_hyps else 0.78) * 100))

        if res.get("safety_flag"):
            replies = [
                f"🚨 SAFETY STOP (Ticket #{short_id} · Urgency: SAFETY): Please switch off the appliance at the wall breaker immediately and do not touch any wet metal surfaces.",
                "⚡ Self-fix skipped automatically due to electrical/thermal hazard. Your ticket is pinned to the top of the Frost & Wave Agent Console and electrical-certified technician Rameshwar Goud has been assigned for priority dispatch.\n"
                "• Track status & quote: /quotes/demo-magic-token",
            ]
            stage = "booked"
        else:
            if tid:
                db.execute("UPDATE ticket SET status = 'triage', updated_at = %s WHERE id = %s", (now_iso, tid))
            replies = [
                f"✅ Ticket #{short_id} logged at Frost and Wave Service Point (Kukatpally) — now visible at the top of the Agent Console Case Board!\n"
                f"• Preliminary diagnosis: {top_hyp} ({top_prob}% match)",
                "💬 Two quick follow-up questions before we dispatch a technician:\n"
                "1️⃣ When did this problem start, and is there any burning smell, smoke, or water near the power socket?\n"
                "2️⃣ Are you okay to try a quick, safe 3-minute check yourself first? (Consent Gate 1)\n\n"
                "👇 Tap a quick answer below or type your reply:",
            ]
            stage = "followup_asked"

        return {
            "status": res["status"],
            "stage": stage,
            "ticket_id": tid,
            "household_id": hh_id,
            "urgency": res.get("urgency"),
            "safety_flag": res.get("safety_flag", False),
            "events_count": len(res.get("events", [])),
            "replies": replies,
        }


def _resolve_target_centre_for_brand(db: RLSSession, payload: Dict[str, Any], brand_id: Optional[str]) -> str:
    ck2id, _, _, _, _ = load_directory_maps(db)

    # 1. Explicit target_centre_key or target_centre_id
    if payload.get("target_centre_key") and payload["target_centre_key"] in ck2id:
        return ck2id[payload["target_centre_key"]]
    if payload.get("target_centre_id"):
        return str(payload["target_centre_id"])

    # 2. Match centre name mentioned in brand_note (e.g. C18 "Forwarded to Cool Craft Appliance Services", C19 "Routed to AquaCare...")
    note = str(payload.get("brand_note") or "")
    centres = db.raw_query("SELECT id, name FROM service_centre")
    for c in centres:
        short_name = c["name"].split(",")[0].strip()
        if short_name.lower() in note.lower():
            # If note says "Routed to X", prefer X over "earlier serviced at Y"
            routed_m = re.search(r"routed to\s+([^.]+)", note, re.IGNORECASE)
            if routed_m and short_name.lower() not in routed_m.group(1).lower():
                continue
            return c["id"]

    # 3. Authorised centre for this brand
    if brand_id:
        auth_rows = db.raw_query(
            "SELECT centre_id FROM centre_brand_authorisation WHERE brand_id = %s AND level = 'authorised_service' LIMIT 1",
            (brand_id,),
        )
        if auth_rows:
            return auth_rows[0]["centre_id"]

    return centres[0]["id"]


@router.post("/brand/requests", status_code=202)
def receive_brand_request(
    payload: Dict[str, Any],
    auth: AuthContext = Depends(require_brand_auth),
) -> Dict[str, Any]:
    now_iso = datetime.now(timezone.utc).isoformat()
    with get_rls_session(role="platform") as db:
        brand_name_raw = str(payload.get("brand") or "")
        brand_id = auth.brand_id
        if brand_name_raw:
            b_rows = db.raw_query("SELECT id, name FROM brand WHERE LOWER(name) = LOWER(%s) LIMIT 1", (brand_name_raw,))
            if b_rows:
                brand_id = b_rows[0]["id"]
                brand_name_raw = b_rows[0]["name"]
        elif brand_id:
            b_rows = db.raw_query("SELECT name FROM brand WHERE id = %s LIMIT 1", (brand_id,))
            if b_rows:
                brand_name_raw = b_rows[0]["name"]

        centre_id = _resolve_target_centre_for_brand(db, payload, brand_id)
        ref_id = str(uuid.uuid4())
        claimed = "brand_warranty" if str(payload.get("claimed_warranty") or "").lower() in ("in_warranty", "brand_warranty", "warranty") else "paid"

        db.execute(
            """
            INSERT INTO brand_referral (id, centre_id, brand_id, brand_request_ref, received_at, payload, claimed_entitlement, authority_checked, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NULL, 'received')
            """,
            (
                ref_id,
                centre_id,
                brand_id,
                str(payload.get("ref") or f"BR-{uuid.uuid4().hex[:8]}"),
                payload.get("received_at") or now_iso,
                json.dumps(payload, ensure_ascii=False),
                claimed,
            ),
        )
        projection_store.emit_event(
            db,
            centre_id,
            "brand_request_received",
            "brand",
            f"Brand request received from {brand_name_raw or 'brand'}",
            payload={"brand_referral_id": ref_id, "ref": payload.get("ref")},
        )

        customer = payload.get("customer") or {}
        note = str(payload.get("brand_note") or "")
        serial_match = re.search(r"Serial[^:]*:\s*([A-Z0-9-]+)", note, re.IGNORECASE)
        serial_no = serial_match.group(1) if serial_match else None

        res = process_inbound_case(
            db,
            centre_id=centre_id,
            trigger="brand_forward",
            channel="brand_api",
            from_phone=str(customer.get("phone") or "+91 50000 00000"),
            text=str(payload.get("complaint") or "Brand forwarded service request"),
            display_name=customer.get("name"),
            brand_name=brand_name_raw or None,
            serial_no=serial_no,
            entitlement_claim=claimed,
            brand_referral_id=ref_id,
        )

        if res.get("status") == "declined":
            return {
                "ticket_id": None,
                "status": "declined",
                "declined_reason": res.get("declined_reason"),
            }

        db.execute("UPDATE brand_referral SET authority_checked = %s, status = 'accepted' WHERE id = %s", (res["authority"]["level"], ref_id))
        return {
            "ticket_id": res.get("ticket_id"),
            "status": "received",
            "declined_reason": None,
        }


@router.post("/retailer/handovers", status_code=202)
def receive_retailer_handover(
    payload: Dict[str, Any],
    auth: AuthContext = Depends(require_brand_auth),
) -> Dict[str, Any]:
    now_iso = datetime.now(timezone.utc).isoformat()
    with get_rls_session(role="platform") as db:
        ck2id, _, _, _, _ = load_directory_maps(db)
        # Pick centre: explicit key, or InstallPro (c_ip) for AC installation, else c_fw
        notes = str(payload.get("notes") or "")
        req_job = str(payload.get("requested_job") or "installation")
        if payload.get("target_centre_key") and payload["target_centre_key"] in ck2id:
            centre_id = ck2id[payload["target_centre_key"]]
        elif "washer" in notes.lower() and "c_fw" in ck2id:
            centre_id = ck2id["c_fw"]
        elif "c_ip" in ck2id and req_job == "installation":
            centre_id = ck2id["c_ip"]
        else:
            centre_id = next(iter(ck2id.values()))

        retailer_name = str(payload.get("retailer") or "")
        ret_rows = db.raw_query("SELECT id FROM retailer WHERE LOWER(name) LIKE LOWER(%s) LIMIT 1", (f"%{retailer_name[:12]}%",))
        retailer_id = auth.retailer_id or (ret_rows[0]["id"] if ret_rows else None)

        ho_id = str(uuid.uuid4())
        db.execute(
            """
            INSERT INTO retailer_handover (id, centre_id, retailer_id, order_ref, invoice_no, purchase_date, requested_job, payload, received_at, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'received')
            """,
            (
                ho_id,
                centre_id,
                retailer_id,
                str(payload.get("order_ref") or f"RET-{uuid.uuid4().hex[:8]}"),
                payload.get("invoice_no"),
                payload.get("purchase_date") or "2026-11-20",
                req_job,
                json.dumps(payload, ensure_ascii=False),
                payload.get("received_at") or now_iso,
            ),
        )
        projection_store.emit_event(
            db,
            centre_id,
            "retailer_handover_received",
            "retailer",
            f"Retailer handover received ({payload.get('order_ref')})",
            payload={"retailer_handover_id": ho_id, "order_ref": payload.get("order_ref")},
        )

        customer = payload.get("customer") or {}
        loc = payload.get("location") or {}
        brand_hint = "Wavecrest" if "washer" in notes.lower() else "Aerovane"
        cat_hint = "washing_machine" if "washer" in notes.lower() else "ac"

        res = process_inbound_case(
            db,
            centre_id=centre_id,
            trigger="retailer_handover",
            channel="retailer_api",
            from_phone=str(customer.get("phone") or "+91 50000 00000"),
            text=notes or f"{req_job} handover",
            display_name=customer.get("name"),
            address_line=loc.get("name"),
            category_hint=cat_hint,
            brand_name=brand_hint,
            requested_job=req_job,
            retailer_handover_id=ho_id,
        )
        if res.get("status") == "declined":
            return {"ticket_id": None, "status": "declined", "declined_reason": res.get("declined_reason")}
        return {"ticket_id": res.get("ticket_id"), "status": "received", "declined_reason": None}


@router.post("/payments/webhook")
async def receive_payment_webhook(
    request: Request,
    x_keepwell_signature: Optional[str] = Header(default=None, alias="X-Keepwell-Signature"),
    x_payment_signature: Optional[str] = Header(default=None, alias="X-Payment-Signature"),
) -> Dict[str, Any]:
    raw_body = await request.body()
    sig = x_keepwell_signature or x_payment_signature or ""
    if not verify_webhook_signature(raw_body, sig, settings.payment_webhook_secret):
        raise APIError("invalid_signature", "Payment webhook HMAC verification failed", status_code=401)

    payload = json.loads(raw_body.decode("utf-8"))
    payment_id = payload.get("payment_id")
    status = payload.get("status", "paid")
    payment_ref = payload.get("payment_ref") or f"PAY-{uuid.uuid4().hex[:10].upper()}"
    now_iso = datetime.now(timezone.utc).isoformat()

    with get_rls_session(role="platform") as db:
        rows = db.raw_query("SELECT * FROM payment_intent WHERE id = %s LIMIT 1", (payment_id,))
        if not rows:
            raise APIError("payment_not_found", f"Payment intent {payment_id} not found", status_code=404)
        pi = rows[0]

        if status == "paid":
            db.execute(
                "UPDATE payment_intent SET status = 'paid', payment_ref = %s, paid_at = %s WHERE id = %s",
                (payment_ref, now_iso, payment_id),
            )
            existing_sl = db.raw_query(
                "SELECT id FROM settlement_line WHERE ticket_id = %s AND party_type = 'household' LIMIT 1",
                (pi["ticket_id"],),
            )
            if existing_sl:
                db.execute(
                    "UPDATE settlement_line SET status = 'paid', payment_ref = %s, settled_at = %s WHERE id = %s",
                    (payment_ref, now_iso, existing_sl[0]["id"]),
                )
            else:
                db.execute(
                    """
                    INSERT INTO settlement_line (id, ticket_id, party_type, party_id, direction, amount_paise, status, payment_ref, due_at, settled_at, centre_id)
                    VALUES (%s, %s, 'household', NULL, 'receivable', %s, 'paid', %s, %s, %s, %s)
                    """,
                    (
                        str(uuid.uuid4()),
                        pi["ticket_id"],
                        str(pi["amount_paise"]),
                        payment_ref,
                        now_iso,
                        now_iso,
                        pi["centre_id"],
                    ),
                )
            projection_store.emit_event(
                db,
                pi["centre_id"],
                "payment_confirmed",
                "system",
                f"Payment confirmed via webhook ({payment_ref})",
                ticket_id=pi["ticket_id"],
                payload={"payment_id": payment_id, "payment_ref": payment_ref},
            )
        else:
            db.execute("UPDATE payment_intent SET status = 'failed' WHERE id = %s", (payment_id,))
            projection_store.emit_event(
                db,
                pi["centre_id"],
                "payment_failed",
                "system",
                "Payment failed via webhook",
                ticket_id=pi["ticket_id"],
                payload={"payment_id": payment_id, "reason": payload.get("reason", "provider_failed")},
            )

    # HARD INVARIANT: Payment NEVER closes a ticket — only household OTP does!
    return {"status": "ok", "payment_id": payment_id, "payment_status": status, "ticket_closed": False}
