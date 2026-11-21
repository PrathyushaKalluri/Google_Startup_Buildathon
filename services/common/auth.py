from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from services.common.config import settings
from services.common.crypto import mint_magic_token, verify_magic_token

_FIREBASE_APP_INIT = False


def _ensure_firebase_app() -> None:
    global _FIREBASE_APP_INIT
    if _FIREBASE_APP_INIT:
        return
    import firebase_admin  # type: ignore

    if not firebase_admin._apps:
        firebase_admin.initialize_app(options={"projectId": settings.firebase_project_id})
    _FIREBASE_APP_INIT = True


def verify_firebase_id_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify a real Firebase ID token via firebase_admin.auth.verify_id_token()."""
    try:
        _ensure_firebase_app()
        from firebase_admin import auth as fb_auth  # type: ignore

        claims = fb_auth.verify_id_token(token)
        claims["_auth_backend"] = "real_firebase_auth"
        return claims
    except Exception:
        return None


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
    Token verification order (Contract C3):
    1. Signed Keepwell magic/custom token (b64.sig) — always verified cryptographically.
    2. 3-segment JWT (header.payload.sig):
       - Always attempts real Firebase Auth `firebase_admin.auth.verify_id_token()` first.
       - Unsigned/emulator JWT fallback ONLY when FIREBASE_AUTH_EMULATOR_HOST or DEMO_MODE=true.
    3. `demo:<email>` — accepted ONLY when FIREBASE_AUTH_EMULATOR_HOST or DEMO_MODE=true.
    """
    allow_dev = bool(
        settings.demo_mode
        or settings.firebase_auth_emulator_host
        or os.getenv("FIREBASE_AUTH_EMULATOR_HOST")
    )

    if token.startswith("demo:"):
        if not allow_dev:
            return None
        return {"email": token[5:], "sub": token[5:], "_auth_backend": "demo_mode"}

    if token.startswith("demo-token-"):
        if not allow_dev:
            return None
        rest = token.removeprefix("demo-token-")
        if rest == "parts":
            email = "parts.demo@keepwell.demo"
        elif rest == "platform":
            email = "platform@keepwell.demo"
        elif rest.startswith("console-"):
            email = f"console.{rest.removeprefix('console-')}@keepwell.demo"
        elif rest.startswith("tech1-"):
            email = f"tech1.{rest.removeprefix('tech1-')}@keepwell.demo"
        elif rest.startswith("tech2-"):
            email = f"tech2.{rest.removeprefix('tech2-')}@keepwell.demo"
        elif rest.startswith("brand-"):
            email = f"brand.{rest.removeprefix('brand-')}@keepwell.demo"
        else:
            email = "console.c_fw@keepwell.demo"
        return {"email": email, "sub": email, "_auth_backend": "demo_mode"}

    if token.count(".") == 1:
        try:
            claims = verify_magic_token(token)
            claims["_auth_backend"] = "signed_magic_token"
            return claims
        except Exception:
            return None

    if token.count(".") == 2:
        verified = verify_firebase_id_token(token)
        if verified is not None:
            return verified
        if not allow_dev:
            return None
        try:
            parts = token.split(".")
            pad = "=" * (-len(parts[1]) % 4)
            claims = json.loads(base64.urlsafe_b64decode(parts[1] + pad).decode("utf-8"))
            claims["_auth_backend"] = "emulator_unsigned_fallback"
            return claims
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
