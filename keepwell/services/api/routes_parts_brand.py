"""Parts centre and Brand/Retailer REST routes (Contract C5.2)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from services.api.deps import APIError, require_brand_auth, require_parts_auth
from services.api.serializers import list_envelope
from services.common.auth import AuthContext
from services.common.db import get_rls_session, parse_pg_json
from services.worker.projections import projection_store

router = APIRouter(tags=["Parts Centre & Brand"])


class StockUpdateRequest(BaseModel):
    part_id: Optional[str] = None
    part_no: Optional[str] = None
    quantity: int = Field(ge=0)


@router.get("/partscentre/requests")
def list_partscentre_requests(auth: AuthContext = Depends(require_parts_auth)) -> Dict[str, Any]:
    with get_rls_session(role="platform") as db:
        if auth.parts_centre_id:
            rows = db.raw_query(
                "SELECT * FROM reservation WHERE holder_type = 'parts_centre' AND holder_id = %s ORDER BY created_at DESC",
                (auth.parts_centre_id,),
            )
            if not rows:
                rows = db.raw_query("SELECT * FROM reservation ORDER BY created_at DESC")
        else:
            rows = db.raw_query("SELECT * FROM reservation ORDER BY created_at DESC")
        parts_by_id = {p["id"]: p for p in db.raw_query("SELECT id, part_no, name FROM part_catalogue")}
        items = [
            {
                "id": r["id"],
                "centre_id": r["centre_id"],
                "visit_id": r.get("visit_id"),
                "part_id": r.get("part_id"),
                "part_no": parts_by_id.get(r.get("part_id"), {}).get("part_no"),
                "part_name": parts_by_id.get(r.get("part_id"), {}).get("name"),
                "quantity": int(r.get("quantity") or 1),
                "holder_type": r.get("holder_type"),
                "holder_id": r.get("holder_id"),
                "ready_by": r.get("ready_by"),
                "status": r.get("status"),
                "created_at": r.get("created_at"),
            }
            for r in rows
        ]
        return list_envelope(items)


def _transition_parts_request(req_id: str, new_status: str) -> Dict[str, Any]:
    with get_rls_session(role="platform") as db:
        rows = db.raw_query("SELECT * FROM reservation WHERE id = %s LIMIT 1", (req_id,))
        if not rows:
            raise APIError("parts_request_not_found", f"Parts request {req_id} not found", status_code=404)
        r = rows[0]
        db_status = {"accepted": "confirmed", "ready": "confirmed", "handed_over": "collected"}.get(new_status, new_status)
        db.execute("UPDATE reservation SET status = %s WHERE id = %s", (db_status, req_id))
        projection_store.project_parts_request(
            r["centre_id"],
            req_id,
            {
                "visit_id": r.get("visit_id"),
                "part_no": r.get("part_id"),
                "quantity": int(r.get("quantity") or 1),
                "status": new_status,
                "parts_centre_id": r.get("holder_id") if r.get("holder_type") == "parts_centre" else None,
            },
        )
        return {
            "id": req_id,
            "centre_id": r["centre_id"],
            "visit_id": r.get("visit_id"),
            "part_id": r.get("part_id"),
            "quantity": int(r.get("quantity") or 1),
            "status": new_status,
        }


@router.post("/partscentre/requests/{req_id}/accept")
def accept_parts_request(req_id: str, auth: AuthContext = Depends(require_parts_auth)) -> Dict[str, Any]:
    return _transition_parts_request(req_id, "accepted")


@router.post("/partscentre/requests/{req_id}/ready")
def ready_parts_request(req_id: str, auth: AuthContext = Depends(require_parts_auth)) -> Dict[str, Any]:
    return _transition_parts_request(req_id, "ready")


@router.post("/partscentre/requests/{req_id}/handover")
def handover_parts_request(req_id: str, auth: AuthContext = Depends(require_parts_auth)) -> Dict[str, Any]:
    return _transition_parts_request(req_id, "handed_over")


@router.put("/partscentre/stock")
def update_partscentre_stock(
    body: StockUpdateRequest,
    auth: AuthContext = Depends(require_parts_auth),
) -> Dict[str, Any]:
    now_iso = datetime.now(timezone.utc).isoformat()
    with get_rls_session(role="platform") as db:
        pc_id = auth.parts_centre_id
        if not pc_id:
            pcs = db.raw_query("SELECT id FROM parts_centre LIMIT 1")
            pc_id = pcs[0]["id"] if pcs else str(uuid.uuid4())

        part_id = body.part_id
        if not part_id and body.part_no:
            found = db.raw_query("SELECT id FROM part_catalogue WHERE part_no = %s LIMIT 1", (body.part_no,))
            if not found:
                raise APIError("unknown_part", f"Part {body.part_no} not found", status_code=404, field="part_no")
            part_id = found[0]["id"]
        if not part_id:
            raise APIError("missing_part_id", "part_id or part_no required", status_code=400)

        existing = db.raw_query(
            "SELECT id FROM stock WHERE holder_type = 'parts_centre' AND holder_id = %s AND part_id = %s LIMIT 1",
            (pc_id, part_id),
        )
        if existing:
            stock_id = existing[0]["id"]
            db.execute(
                "UPDATE stock SET quantity = %s, as_of = %s WHERE id = %s",
                (str(body.quantity), now_iso, stock_id),
            )
        else:
            stock_id = str(uuid.uuid4())
            db.execute(
                """
                INSERT INTO stock (id, holder_type, holder_id, centre_id, part_id, quantity, as_of, source, confidence)
                VALUES (%s, 'parts_centre', %s, NULL, %s, %s, %s, 'api', '1.0')
                """,
                (stock_id, pc_id, part_id, str(body.quantity), now_iso),
            )
        return {"id": stock_id, "parts_centre_id": pc_id, "part_id": part_id, "quantity": body.quantity, "as_of": now_iso}


@router.get("/brand/requests")
def list_brand_requests(auth: AuthContext = Depends(require_brand_auth)) -> Dict[str, Any]:
    with get_rls_session(role="platform") as db:
        if auth.brand_id:
            rows = db.raw_query(
                "SELECT * FROM brand_referral WHERE brand_id = %s ORDER BY received_at DESC",
                (auth.brand_id,),
            )
        else:
            rows = db.raw_query("SELECT * FROM brand_referral ORDER BY received_at DESC")
        items = [
            {
                "id": r["id"],
                "centre_id": r["centre_id"],
                "brand_id": r["brand_id"],
                "brand_request_ref": r.get("brand_request_ref"),
                "received_at": r.get("received_at"),
                "claimed_entitlement": r.get("claimed_entitlement"),
                "authority_checked": r.get("authority_checked"),
                "status": r.get("status"),
                "payload": parse_pg_json(r.get("payload"), {}),
            }
            for r in rows
        ]
        return list_envelope(items)


@router.get("/brand/analytics")
def brand_analytics(auth: AuthContext = Depends(require_brand_auth)) -> Dict[str, Any]:
    with get_rls_session(role="platform") as db:
        if auth.brand_id:
            appliances = db.raw_query("SELECT * FROM appliance WHERE brand_id = %s", (auth.brand_id,))
            auths = db.raw_query("SELECT * FROM centre_brand_authorisation WHERE brand_id = %s", (auth.brand_id,))
            brand_rows = db.raw_query("SELECT name FROM brand WHERE id = %s LIMIT 1", (auth.brand_id,))
            brand_name = brand_rows[0]["name"] if brand_rows else "Brand"
        else:
            appliances = db.raw_query("SELECT * FROM appliance")
            auths = db.raw_query("SELECT * FROM centre_brand_authorisation")
            brand_name = "All Brands"

        app_ids = {a["id"] for a in appliances}
        all_tickets = db.raw_query("SELECT * FROM ticket")
        brand_tickets = [t for t in all_tickets if t.get("appliance_id") in app_ids]
        bt_ids = {t["id"] for t in brand_tickets}

        visits = [v for v in db.raw_query("SELECT * FROM visit") if v["ticket_id"] in bt_ids]
        visits_by_ticket: Dict[str, List[Dict[str, Any]]] = {}
        for v in visits:
            visits_by_ticket.setdefault(v["ticket_id"], []).append(v)

        ftf_num = 0
        ftf_den = 0
        fvr_num = 0
        t_map = {t["id"]: t for t in brand_tickets}
        for tid, vlist in visits_by_ticket.items():
            vlist.sort(key=lambda x: x.get("created_at") or "")
            if vlist[0].get("outcome"):
                ftf_den += 1
                if vlist[0].get("outcome") == "fixed" and len(vlist) == 1:
                    ftf_num += 1
                    if t_map.get(tid, {}).get("closure_confirmed_at") or vlist[0].get("closure_confirmed_at"):
                        fvr_num += 1

        by_category: Dict[str, int] = {}
        for a in appliances:
            cat = a.get("category_code") or "other"
            by_category[cat] = by_category.get(cat, 0) + 1

        return {
            "brand_id": auth.brand_id,
            "brand_name": brand_name,
            "installed_base": {
                "total_appliances": len(appliances),
                "by_category": by_category,
            },
            "service_quality": {
                "total_tickets": len(brand_tickets),
                "open_tickets": sum(1 for t in brand_tickets if t.get("status") not in ("closed", "cancelled")),
                "closed_tickets": sum(1 for t in brand_tickets if t.get("status") == "closed"),
                "first_time_fix": round(ftf_num / ftf_den, 4) if ftf_den else 0.0,
                "fvr_14d": round(fvr_num / ftf_den, 4) if ftf_den else 0.0,
            },
            "authorised_centres_count": sum(1 for a in auths if a.get("level") == "authorised_service"),
        }
