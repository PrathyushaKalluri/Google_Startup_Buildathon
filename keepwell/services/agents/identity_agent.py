from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from services.common.db import RLSSession

SERIAL_RE = re.compile(r"\b([A-Z]{2,4}[-]?[A-Z0-9]{4,14})\b")


def normalise_serial(serial: Optional[str]) -> Optional[str]:
    if not serial:
        return None
    cleaned = re.sub(r"[^A-Za-z0-9]", "", serial).upper()
    return cleaned or None


def resolve_identity(
    db: RLSSession,
    centre_id: str,
    phone: str,
    verified_via: str = "call_line",
    display_name: Optional[str] = None,
    language: str = "en",
    address_line: Optional[str] = None,
    pincode: Optional[str] = None,
    category_code: Optional[str] = None,
    brand_name: Optional[str] = None,
    model_code: Optional[str] = None,
    serial_no: Optional[str] = None,
) -> Dict[str, Any]:
    """
    ADK Identity Agent:
    1. Resolves or creates global household via db.identify_household() (phone hash + external_ref).
    2. Resolves appliance via (brand_id + serial_norm) or existing household appliances matching category.
    3. Assigns evidence_level: confirmed | probable | unverified (never lets unverified drive parts).
    """
    hh_info = db.identify_household(
        phone=phone,
        centre_id=centre_id,
        verified_via=verified_via,
        display_name=display_name,
        language=language,
        address_line=address_line,
        pincode=pincode,
    )
    hid = hh_info["household_id"]
    hh_row = db.raw_query("SELECT * FROM household WHERE id = ?", (hid,))[0]

    # Resolve brand_id if brand_name given
    brand_id: Optional[str] = None
    if brand_name:
        b = db.raw_query("SELECT id FROM brand WHERE lower(name) = lower(?) LIMIT 1", (brand_name,))
        if b:
            brand_id = b[0]["id"]

    # 1. Exact global lookup by brand + serial_norm (Q2)
    serial_norm = normalise_serial(serial_no)
    appliance_row: Optional[Dict[str, Any]] = None
    evidence_level = "unverified"
    identity_source = "record"

    if serial_norm:
        if brand_id:
            rows = db.raw_query(
                "SELECT * FROM appliance WHERE brand_id = ? AND serial_norm = ? AND identity_status <> 'merged' LIMIT 1",
                (brand_id, serial_norm),
            )
        else:
            rows = db.raw_query(
                "SELECT * FROM appliance WHERE serial_norm = ? AND identity_status <> 'merged' LIMIT 1",
                (serial_norm,),
            )
        if rows:
            appliance_row = rows[0]
            evidence_level = "confirmed"
            identity_source = "sticker"

    # 2. Household's existing active appliances matching category (and brand if known)
    if appliance_row is None:
        hh_apps = db.raw_query(
            "SELECT * FROM appliance WHERE household_id = ? AND status = 'active' ORDER BY created_at DESC",
            (hid,),
        )
        if category_code:
            cat_matches = [a for a in hh_apps if a["category_code"] == category_code]
            if brand_id:
                brand_matches = [a for a in cat_matches if a["brand_id"] == brand_id]
                if brand_matches:
                    appliance_row = brand_matches[0]
            if appliance_row is None and cat_matches:
                appliance_row = cat_matches[0]
        elif hh_apps:
            appliance_row = hh_apps[0]

        if appliance_row is not None:
            evidence_level = "confirmed" if appliance_row.get("identity_status") == "verified" else "probable"
            identity_source = "record"

    # 3. Create new appliance if none matched
    if appliance_row is None:
        if not brand_id:
            b = db.raw_query("SELECT id FROM brand LIMIT 1")
            brand_id = b[0]["id"] if b else str(uuid.uuid4())
        model_id = None
        if model_code:
            m = db.raw_query(
                "SELECT id, brand_id FROM appliance_model WHERE lower(model_code) = lower(?) LIMIT 1",
                (model_code,),
            )
            if m:
                model_id = m[0]["id"]
                brand_id = m[0]["brand_id"]

        app_id = str(uuid.uuid4())
        now_iso = datetime.now(timezone.utc).isoformat()
        id_status = "verified" if serial_norm else "provisional"
        evidence_level = "confirmed" if (serial_norm and model_id) else ("probable" if model_id else "unverified")
        appliance_row = {
            "id": app_id,
            "household_id": hid,
            "category_code": category_code or "ac",
            "brand_id": brand_id,
            "model_id": model_id,
            "model_text": model_code,
            "serial_no": serial_no,
            "serial_norm": serial_norm,
            "identity_status": id_status,
            "evidence_level": evidence_level,
            "first_seen_via": "retailer" if verified_via == "retailer_record" else ("brand" if verified_via == "brand_record" else "household"),
            "first_seen_centre_id": centre_id,
            "status": "active",
            "created_at": now_iso,
            "updated_at": now_iso,
        }
        db.insert("appliance", appliance_row)
        identity_source = "invoice" if verified_via == "retailer_record" else "record"

    # Enrich brand & model metadata
    b_row = db.raw_query("SELECT name FROM brand WHERE id = ?", (appliance_row["brand_id"],))
    brand_label = b_row[0]["name"] if b_row else (brand_name or "Unknown")
    m_code = appliance_row.get("model_text")
    if appliance_row.get("model_id"):
        m_row = db.raw_query("SELECT model_code FROM appliance_model WHERE id = ?", (appliance_row["model_id"],))
        if m_row:
            m_code = m_row[0]["model_code"]

    return {
        "household": hh_row,
        "household_lookup": hh_info,
        "appliance": appliance_row,
        "brand_name": brand_label,
        "model_code": m_code,
        "evidence_level": evidence_level,
        "identity_source": identity_source,
    }
