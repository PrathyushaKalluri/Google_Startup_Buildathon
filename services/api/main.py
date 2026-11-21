"""Keepwell Part A FastAPI application entrypoint (Contract C5 & C7)."""
from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Dict

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


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Fail fast at startup if DATABASE_URL is not PostgreSQL 16."""
    settings.require_postgres()
    yield


app = FastAPI(
    title="Keepwell REST API v1",
    version="1.0.0",
    description="Keepwell service-centre and brand platform API (Part A: Agent Core).",
    openapi_url="/openapi.json",
    lifespan=lifespan,
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
    import psycopg

    if isinstance(exc, psycopg.errors.InvalidTextRepresentation) and "uuid" in str(exc).lower():
        return make_error_response("not_found", "Resource not found", status_code=404)
    return make_error_response("internal_error", str(exc), status_code=500)


# ---- Global Health, Meta, MCP, and Live Call WebSocket ----


@app.get("/healthz", tags=["System"])
def healthz() -> Dict[str, Any]:
    return {"status": "ok", "service": "kw-api", "time": datetime.now(timezone.utc).isoformat()}


@app.get("/readyz", tags=["System"])
def readyz() -> Dict[str, Any]:
    settings.require_postgres()
    with get_rls_session(role="platform") as db:
        centres = db.raw_query("SELECT COUNT(*) AS c FROM kw.service_centre")[0]["c"]
    return {"status": "ready", "centres": int(centres), "database": "postgresql"}


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


# ---- Unified 4-in-1 Prototype Hub & Static App Mounts ----

from fastapi.responses import FileResponse, HTMLResponse
from services.common.config import KEEPWELL_ROOT

_UNIFIED_HUB_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Keepwell — Unified 4-Surface Prototype Hub</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: system-ui, -apple-system, sans-serif; background: #0f172a; color: #f8fafc; height: 100vh; display: flex; flex-direction: column; overflow: hidden; }
    header { display: flex; align-items: center; gap: 8px; padding: 8px 14px; background: #1e293b; border-bottom: 1px solid #334155; flex-wrap: wrap; }
    .brand { font-weight: 700; font-size: 15px; color: #38bdf8; margin-right: 10px; display: flex; align-items: center; gap: 6px; }
    .badge { font-size: 11px; background: #065f46; color: #6ee7b7; padding: 2px 8px; border-radius: 999px; font-weight: 600; }
    .tab-btn { background: #334155; color: #e2e8f0; border: 1px solid #475569; padding: 6px 12px; border-radius: 8px; cursor: pointer; font-size: 13px; font-weight: 600; transition: all 0.15s; }
    .tab-btn:hover { background: #475569; }
    .tab-btn.active { background: #0284c7; color: #ffffff; border-color: #38bdf8; }
    .spacer { flex: 1; }
    .action-btn { background: #0f766e; color: #fff; border: none; padding: 6px 11px; border-radius: 8px; cursor: pointer; font-size: 12px; font-weight: 600; }
    .action-btn:hover { background: #115e59; }
    main { flex: 1; display: flex; width: 100%; height: calc(100vh - 49px); background: #0f172a; }
    .pane { height: 100%; border: none; background: #fff; display: none; flex-direction: column; }
    .pane.visible { display: flex; }
    .pane-header { background: #f1f5f9; color: #0f172a; font-size: 12px; font-weight: 700; padding: 4px 12px; border-bottom: 1px solid #cbd5e1; display: flex; justify-content: space-between; align-items: center; }
    iframe { flex: 1; width: 100%; height: 100%; border: none; }
    .split-left { width: 42%; border-right: 3px solid #334155; }
    .split-right { width: 58%; }
    .full-width { width: 100%; }
  </style>
</head>
<body>
  <header>
    <div class="brand">Keepwell Unified Prototype <span class="badge">Live Local PG18 · $0 Credits</span></div>
    <button class="tab-btn active" onclick="setMode('split')" id="btn-split">⚡ Split View: Household + Agent Console</button>
    <button class="tab-btn" onclick="setMode('household')" id="btn-household">1. Household (Customer)</button>
    <button class="tab-btn" onclick="setMode('console')" id="btn-console">2. Agent Console &amp; Stage</button>
    <button class="tab-btn" onclick="setMode('field')" id="btn-field">3. Field (Technician &amp; Parts)</button>
    <button class="tab-btn" onclick="setMode('brand')" id="btn-brand">4. Brand &amp; Retailer</button>
    <div class="spacer"></div>
    <button class="action-btn" onclick="syncFrames()">🔄 Refresh Views</button>
  </header>
  <main>
    <div class="pane visible split-left" id="pane-household">
      <div class="pane-header"><span>1. HOUSEHOLD COMPANION (Send a complaint here → appears in Agent Console on right)</span></div>
      <iframe id="frame-household" src="/app/household/"></iframe>
    </div>
    <div class="pane visible split-right" id="pane-console">
      <div class="pane-header"><span>2. CENTRE CONSOLE &amp; LIVE STAGE VIEW (Auto-signed in: Frost &amp; Wave, Kukatpally)</span></div>
      <iframe id="frame-console" src="/app/console/?demo=1"></iframe>
    </div>
    <div class="pane full-width" id="pane-field">
      <div class="pane-header"><span>3. FIELD APP — TECHNICIAN (tech1.c_fw@keepwell.demo) &amp; PARTS CENTRE (parts.demo@keepwell.demo)</span></div>
      <iframe id="frame-field" src="/app/field/"></iframe>
    </div>
    <div class="pane full-width" id="pane-brand">
      <div class="pane-header"><span>4. BRAND &amp; RETAILER PORTAL (brand.aerovane@keepwell.demo)</span></div>
      <iframe id="frame-brand" src="/app/brand/"></iframe>
    </div>
  </main>
  <script>
    function setMode(mode) {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.getElementById('btn-' + mode).classList.add('active');
      const hh = document.getElementById('pane-household');
      const con = document.getElementById('pane-console');
      const fld = document.getElementById('pane-field');
      const brd = document.getElementById('pane-brand');
      [hh, con, fld, brd].forEach(p => { p.className = 'pane'; });
      if (mode === 'split') {
        hh.className = 'pane visible split-left';
        con.className = 'pane visible split-right';
      } else if (mode === 'household') {
        hh.className = 'pane visible full-width';
      } else if (mode === 'console') {
        con.className = 'pane visible full-width';
      } else if (mode === 'field') {
        fld.className = 'pane visible full-width';
      } else if (mode === 'brand') {
        brd.className = 'pane visible full-width';
      }
    }
    function syncFrames() {
      const cf = document.getElementById('frame-console');
      if (cf) cf.contentWindow.location.reload();
    }
  </script>
</body>
</html>"""


@app.get("/", include_in_schema=False)
def unified_prototype_hub() -> HTMLResponse:
    return HTMLResponse(_UNIFIED_HUB_HTML)


@app.get("/app/{app_name}", include_in_schema=False)
@app.get("/app/{app_name}/", include_in_schema=False)
def serve_flutter_app_index(app_name: str) -> HTMLResponse:
    if app_name not in ("console", "household", "field", "brand"):
        raise HTTPException(status_code=404, detail="Unknown app")
    idx = KEEPWELL_ROOT / "apps" / app_name / "build" / "web" / "index.html"
    if not idx.exists():
        return HTMLResponse(f"<h3>Building {app_name}... refresh in 30s.</h3>", status_code=503)
    html = idx.read_text(encoding="utf-8").replace('<base href="/">', f'<base href="/app/{app_name}/">')
    return HTMLResponse(html)


@app.get("/app/{app_name}/{asset_path:path}", include_in_schema=False)
def serve_flutter_app_asset(app_name: str, asset_path: str) -> Any:
    if app_name not in ("console", "household", "field", "brand"):
        raise HTTPException(status_code=404, detail="Unknown app")
    base_dir = (KEEPWELL_ROOT / "apps" / app_name / "build" / "web").resolve()
    target = (base_dir / asset_path).resolve()
    if str(target).startswith(str(base_dir)) and target.is_file():
        return FileResponse(target)
    idx = base_dir / "index.html"
    if idx.exists():
        html = idx.read_text(encoding="utf-8").replace('<base href="/">', f'<base href="/app/{app_name}/">')
        return HTMLResponse(html)
    raise HTTPException(status_code=404, detail="Asset not found")
