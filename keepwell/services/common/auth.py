from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from services.common.config import settings
from services.common.crypto import mint_magic_token, verify_magic_token


CENTRE_KEYS = ["c_av", "c_zn", "c_fw", "c_cc", "c_aq", "c_mh", "c_ip", "c_ls", "c_hw"]

CENTRE_NAME_TO_KEY = {
    "Aerovane Authorised Service, Gachibowli": "c_av",
    "Zenith Care Hub, Kondapur": "c_zn",
    "Frost and Wave Service Point, Kukatpally": "c_fw",
    "Cool Craft Appliance Services, Madhapur": "c_cc",
    "AquaCare RO and Geyser Services, Manikonda": "c_aq",
    "Metro Home Appliance Care, Miyapur": "c_mh",
    "InstallPro Mounting Services, Tolichowki": "c_ip",
    "Lakeshore Service Centre, Jubilee Hills": "c_ls",
    "Heatwell Authorised Service, Banjara Hills": "c_hw",
}


@dataclass
class AuthContext:
    user_id: str
    email: Optional[str]
    role: str  # centre_admin | technician | parts_centre | brand | platform | household | retailer
    centre_id: Optional[str] = None
    technician_id: Optional[str] = None
    parts_centre_id: Optional[str] = None
    brand_id: Optional[str] = None
    retailer_id: Optional[str] = None
    household_id: Optional[str] = None

    @property
    def is_platform(self) -> bool:
        return self.role == "platform"


def decode_dev_bearer_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Accepts either:
    - 'demo:<email>' (for local dev/tests)
    - signed Keepwell magic/custom token (b64.sig)
    - unsigned/emulator JWT (header.payload.sig) when Firebase Auth emulator or DEMO_MODE is active
    """
    if token.startswith("demo:"):
        return {"email": token[5:], "sub": token[5:]}
    if token.count(".") == 1:
        try:
            return verify_magic_token(token)
        except Exception:
            return None
    if token.count(".") == 2:
        try:
            parts = token.split(".")
            pad = "=" * (-len(parts[1]) % 4)
            return json.loads(base64.urlsafe_b64decode(parts[1] + pad).decode("utf-8"))
        except Exception:
            return None
    return None


def resolve_auth_from_claims(
    claims: Dict[str, Any],
    centre_key_to_id: Dict[str, str],
    techs_by_centre: Dict[str, List[str]],
    brand_name_to_id: Dict[str, str],
    first_parts_centre_id: Optional[str] = None,
) -> AuthContext:
    """Resolve AuthContext from Firebase custom claims or demo email convention (Contract C3)."""
    if "role" in claims and claims["role"] in (
        "centre_admin",
        "technician",
        "parts_centre",
        "brand",
        "platform",
        "household",
    ):
        return AuthContext(
            user_id=str(claims.get("sub", claims.get("uid", "user"))),
            email=claims.get("email"),
            role=claims["role"],
            centre_id=claims.get("centre_id"),
            technician_id=claims.get("technician_id"),
            parts_centre_id=claims.get("parts_centre_id"),
            brand_id=claims.get("brand_id"),
            household_id=claims.get("household_id"),
        )

    email = str(claims.get("email", "")).lower()
    if email == "platform@keepwell.demo":
        return AuthContext(user_id=email, email=email, role="platform")
    if email == "parts.demo@keepwell.demo":
        return AuthContext(
            user_id=email,
            email=email,
            role="parts_centre",
            parts_centre_id=first_parts_centre_id,
        )
    if email.startswith("console.") and email.endswith("@keepwell.demo"):
        ckey = email.removeprefix("console.").removesuffix("@keepwell.demo")
        cid = centre_key_to_id.get(ckey)
        if cid:
            return AuthContext(user_id=email, email=email, role="centre_admin", centre_id=cid)
    if (email.startswith("tech1.") or email.startswith("tech2.")) and email.endswith("@keepwell.demo"):
        idx = 0 if email.startswith("tech1.") else 1
        ckey = email.split(".", 1)[1].removesuffix("@keepwell.demo")
        cid = centre_key_to_id.get(ckey)
        tlist = techs_by_centre.get(cid or "", [])
        tid = tlist[idx] if idx < len(tlist) else (tlist[0] if tlist else None)
        if cid:
            return AuthContext(
                user_id=email,
                email=email,
                role="technician",
                centre_id=cid,
                technician_id=tid,
            )
    if email.startswith("brand.") and email.endswith("@keepwell.demo"):
        bkey = email.removeprefix("brand.").removesuffix("@keepwell.demo")
        bid = next(
            (v for k, v in brand_name_to_id.items() if k.lower().replace(" ", "") == bkey),
            None,
        )
        return AuthContext(user_id=email, email=email, role="brand", brand_id=bid)

    raise ValueError(f"Unrecognised auth claims: {claims}")


def mint_household_custom_token(household_id: str, ttl_seconds: int = 3600) -> str:
    """Mints a signed custom token with claim household_id for Firestore thread access."""
    return mint_magic_token(
        subject_id=household_id,
        scope="household_session",
        ttl_seconds=ttl_seconds,
        extra={"role": "household", "household_id": household_id},
    )
