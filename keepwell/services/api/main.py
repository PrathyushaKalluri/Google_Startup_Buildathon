"""Keepwell Part A FastAPI application entrypoint (Contract C5 & C7)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Request, WebSocket
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

# Ensure A2/A4 runtime shims are installed before importing MCP/orchestrator
import services.api  # noqa: F401
from services.agents.orchestrator import handle_live_turn
from services.api.deps import APIError, lookup_centre_by_key, make_error_response
from services.api.routes_admin import router as admin_router
from services.api.routes_channels import router as channels_router
from services.api.routes_console import router as console_router
from services.api.routes_parts_brand import router as parts_brand_router
from services.api.routes_public import router as public_router
from services.api.routes_technician import router as technician_router
from services.common.config import settings
from services.common.db import get_rls_session
from services.common.logging import new_request_id
from services.live.bridge import handle_live_call_ws
from services.mcp.server import router as mcp_router

app = FastAPI(
    title="Keepwell REST API v1",
    version="1.0.0",
    description="Keepwell service-centre and brand platform API (Part A: Agent Core).",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next: Any) -> Any:
    rid = request.headers.get("X-Request-Id") or new_request_id()
    response = await call_next(request)
    response.headers["X-Request-Id"] = rid
    return response


# ---- Consistent Contract C5 Error Envelope Handlers ----


@app.exception_handler(APIError)
async def api_error_handler(_request: Request, exc: APIError) -> Any:
    return make_error_response(exc.code, exc.message, status_code=exc.status_code, field=exc.field)


@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException) -> Any:
    code = f"http_{exc.status_code}"
    return make_error_response(code, str(exc.detail), status_code=exc.status_code)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request: Request, exc: RequestValidationError) -> Any:
    errs = exc.errors()
    first = errs[0] if errs else {}
    loc = first.get("loc") or []
    field = str(loc[-1]) if loc else None
    msg = first.get("msg", "Validation error")
    return make_error_response("validation_error", msg, status_code=422, field=field)


@app.exception_handler(PermissionError)
async def permission_error_handler(_request: Request, exc: PermissionError) -> Any:
    return make_error_response("forbidden", str(exc), status_code=403)


@app.exception_handler(Exception)
async def unhandled_exception_handler(_request: Request, exc: Exception) -> Any:
    return make_error_response("internal_error", str(exc), status_code=500)


# ---- Global Health, Meta, MCP, and Live Call WebSocket ----


@app.get("/healthz", tags=["System"])
def healthz() -> Dict[str, Any]:
    return {"status": "ok", "service": "kw-api", "time": datetime.now(timezone.utc).isoformat()}


@app.get("/readyz", tags=["System"])
def readyz() -> Dict[str, Any]:
    with get_rls_session(role="platform") as db:
        centres = db.raw_query("SELECT COUNT(*) AS c FROM service_centre")[0]["c"]
    return {"status": "ready", "centres": int(centres), "database": "postgres" if settings.is_postgres else "sqlite"}


@app.get("/v1/meta/version", tags=["System"])
def meta_version() -> Dict[str, Any]:
    return {
        "service": "kw-api",
        "api_version": "v1",
        "contract_version": "1.0",
        "demo_mode": settings.demo_mode,
        "payment_mode": settings.payment_mode,
        "otp_provider": settings.otp_provider,
        "models": {
            "agent": settings.gemini_model_agent,
            "fast": settings.gemini_model_fast,
            "pro": settings.gemini_model_pro,
            "live": settings.gemini_model_live,
            "embed": settings.gemini_model_embed,
        },
    }


app.include_router(mcp_router)


@app.websocket("/v1/live/call")
async def live_call_ws(websocket: WebSocket) -> None:
    await handle_live_call_ws(
        websocket=websocket,
        orchestrator_fn=handle_live_turn,
        centre_lookup_fn=lookup_centre_by_key,
    )


# ---- REST API v1 Routers ----

app.include_router(console_router, prefix="/v1")
app.include_router(technician_router, prefix="/v1")
app.include_router(parts_brand_router, prefix="/v1")
app.include_router(public_router, prefix="/v1")
app.include_router(channels_router, prefix="/v1")
app.include_router(admin_router, prefix="/v1")
