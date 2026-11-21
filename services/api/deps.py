"""FastAPI dependencies, auth resolution, error envelope, and shared services."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from fastapi import Depends, Header
from fastapi.responses import JSONResponse

from services.agents.engines.otp import OTPService
from services.common.auth import (
    CENTRE_NAME_TO_KEY,
    AuthContext,
    decode_dev_bearer_token,
    resolve_auth_from_claims,
)
from services.common.config import settings
from services.common.db import RLSSession, get_rls_session
from services.common.logging import request_id_var

otp_service = OTPService(mode=settings.otp_provider)
idempotency_cache: Dict[str, Any] = {}


class APIError(Exception):
    """Structured API error formatted into the Contract C5 error envelope."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        field: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.field = field


def make_error_response(
    code: str,
    message: str,
    status_code: int = 400,
    field: Optional[str] = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "field": field,
                "request_id": request_id_var.get() or "req-unknown",
            }
        },
    )


def load_directory_maps(
    db: RLSSession,
) -> Tuple[Dict[str, str], Dict[str, str], Dict[str, List[str]], Dict[str, str], Optional[str]]:
    """Return (centre_key_to_id, centre_id_to_key, techs_by_centre, brand_name_to_id, first_parts_centre_id)."""
    centres = db.raw_query("SELECT id, name FROM service_centre ORDER BY id")
    centre_key_to_id: Dict[str, str] = {}
    centre_id_to_key: Dict[str, str] = {}
    for c in centres:
        ckey = CENTRE_NAME_TO_KEY.get(c["name"])
        if ckey:
            centre_key_to_id[ckey] = c["id"]
            centre_id_to_key[c["id"]] = ckey

    techs = db.raw_query("SELECT id, centre_id FROM technician ORDER BY created_at, id")
    techs_by_centre: Dict[str, List[str]] = {}
    for t in techs:
        techs_by_centre.setdefault(t["centre_id"], []).append(t["id"])

    brands = db.raw_query("SELECT id, name FROM brand")
    brand_name_to_id = {b["name"]: b["id"] for b in brands}

    pcs = db.raw_query("SELECT id FROM parts_centre ORDER BY id LIMIT 1")
    first_pc_id = pcs[0]["id"] if pcs else None

    return centre_key_to_id, centre_id_to_key, techs_by_centre, brand_name_to_id, first_pc_id


def lookup_centre_by_key(centre_key: str) -> Optional[Dict[str, Any]]:
    with get_rls_session(role="platform") as db:
        centres = db.raw_query("SELECT * FROM service_centre")
        for c in centres:
            if CENTRE_NAME_TO_KEY.get(c["name"]) == centre_key or c["id"] == centre_key:
                return c
    return None


def _resolve_api_key(db: RLSSession, api_key: str) -> AuthContext:
    """Resolve X-Keepwell-Key to a brand or retailer AuthContext."""
    cleaned = api_key.strip()
    low = cleaned.lower()

    # Check brand match (e.g. 'brand:aerovane', 'kw-brand-aerovane', 'aerovane')
    brands = db.raw_query("SELECT id, name FROM brand")
    for b in brands:
        b_slug = b["name"].lower().replace(" ", "")
        if b_slug in low or cleaned == b["id"]:
            return AuthContext(
                user_id=f"key:brand:{b_slug}",
                email=f"brand.{b_slug}@keepwell.demo",
                role="brand",
                brand_id=b["id"],
            )

    # Check retailer match
    retailers = db.raw_query("SELECT id, name FROM retailer")
    for r in retailers:
        r_slug = r["name"].lower().replace(" ", "")
        if r_slug in low or cleaned == r["id"]:
            return AuthContext(
                user_id=f"key:retailer:{r['id']}",
                email=None,
                role="retailer",
                retailer_id=r["id"],
            )

    # In demo mode, accept any non-empty key prefixed with kw- or demo- as brand/retailer key
    if settings.demo_mode and (low.startswith("kw-") or low.startswith("demo-") or low.startswith("key-")):
        first_brand = brands[0]["id"] if brands else None
        first_retailer = retailers[0]["id"] if retailers else None
        role = "retailer" if "retailer" in low else "brand"
        return AuthContext(
            user_id=f"key:{cleaned}",
            email=None,
            role=role,
            brand_id=first_brand if role == "brand" else None,
            retailer_id=first_retailer if role == "retailer" else None,
        )

    raise APIError("invalid_api_key", "Unrecognised X-Keepwell-Key", status_code=401)


def _resolve_bearer(authorization: Optional[str], x_keepwell_key: Optional[str]) -> Optional[AuthContext]:
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
        claims = decode_dev_bearer_token(token)
        if not claims:
            raise APIError("invalid_token", "Invalid or expired Bearer token", status_code=401)
        with get_rls_session(role="platform") as db:
            ck2id, _, techs_by_c, b2id, first_pc = load_directory_maps(db)
            try:
                return resolve_auth_from_claims(claims, ck2id, techs_by_c, b2id, first_pc)
            except ValueError as exc:
                raise APIError("invalid_claims", str(exc), status_code=401) from exc

    if x_keepwell_key:
        with get_rls_session(role="platform") as db:
            return _resolve_api_key(db, x_keepwell_key)

    return None


def get_current_auth(
    authorization: Optional[str] = Header(default=None),
    x_keepwell_key: Optional[str] = Header(default=None, alias="X-Keepwell-Key"),
) -> AuthContext:
    ctx = _resolve_bearer(authorization, x_keepwell_key)
    if ctx is None:
        raise APIError("unauthorized", "Missing Authorization header", status_code=401)
    return ctx


def require_console_auth(ctx: AuthContext = Depends(get_current_auth)) -> AuthContext:
    if ctx.role not in ("centre_admin", "platform"):
        raise APIError("forbidden", f"Role '{ctx.role}' is not permitted on console routes", status_code=403)
    return ctx


def require_technician_auth(ctx: AuthContext = Depends(get_current_auth)) -> AuthContext:
    if ctx.role not in ("technician", "platform", "centre_admin"):
        raise APIError("forbidden", f"Role '{ctx.role}' is not permitted on technician routes", status_code=403)
    return ctx


def require_parts_auth(ctx: AuthContext = Depends(get_current_auth)) -> AuthContext:
    if ctx.role not in ("parts_centre", "platform"):
        raise APIError("forbidden", f"Role '{ctx.role}' is not permitted on parts-centre routes", status_code=403)
    return ctx


def require_brand_auth(ctx: AuthContext = Depends(get_current_auth)) -> AuthContext:
    if ctx.role not in ("brand", "retailer", "platform"):
        raise APIError("forbidden", f"Role '{ctx.role}' is not permitted on brand routes", status_code=403)
    return ctx


def require_admin_auth(
    authorization: Optional[str] = Header(default=None),
    x_keepwell_key: Optional[str] = Header(default=None, alias="X-Keepwell-Key"),
) -> AuthContext:
    ctx = _resolve_bearer(authorization, x_keepwell_key)
    if ctx is None:
        if settings.demo_mode:
            return AuthContext(user_id="platform@keepwell.demo", email="platform@keepwell.demo", role="platform")
        raise APIError("unauthorized", "Missing Authorization header", status_code=401)
    if ctx.role != "platform" and not settings.demo_mode:
        raise APIError("forbidden", "Admin endpoints require platform role", status_code=403)
    return ctx
