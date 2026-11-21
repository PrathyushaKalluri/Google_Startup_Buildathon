#!/usr/bin/env python3
"""Keepwell Smoke Tests (Part C Section 6.2 I6): health, auth, C03 scripted run, message case, brand decline, projection rebuild, dashboard query."""
from __future__ import annotations

import os
import sys

from fastapi.testclient import TestClient

from services.api.main import app
from services.live.tools.scripted_client import run_c03_scripted_live_call

PLATFORM = {"Authorization": "Bearer demo:platform@keepwell.demo"}
CONSOLE_FW = {"Authorization": "Bearer demo:console.c_fw@keepwell.demo"}


def run_smoke() -> int:
    base_url = os.getenv("KW_SMOKE_URL", "").rstrip("/")
    client = TestClient(app)

    # 1. Health & Ready
    assert client.get("/healthz").status_code == 200
    assert client.get("/readyz").status_code == 200
    print("SMOKE 1/7 PASS: /healthz and /readyz")

    # 2. Auth check (unauthenticated rejected, demo token accepted)
    assert client.get("/v1/tickets").status_code == 401
    assert client.get("/v1/tickets", headers=CONSOLE_FW).status_code == 200
    print("SMOKE 2/7 PASS: Auth enforcement")

    # 3. C03 scripted Live call
    c03 = run_c03_scripted_live_call(client)
    assert c03["ticket_id"] and len(c03["event_types"]) >= 17
    print(f"SMOKE 3/7 PASS: C03 Live WS ({len(c03['event_types'])} events)")

    # 4. Message case (C09)
    m = client.post("/v1/admin/demo/play-case", headers=PLATFORM, json={"case_id": "C09"}).json()
    assert m["ticket_id"]
    print(f"SMOKE 4/7 PASS: Message case C09 -> ticket {m['ticket_id']}")

    # 5. Brand decline (C18)
    b = client.post("/v1/admin/demo/play-case", headers=PLATFORM, json={"case_id": "C18"}).json()
    assert b["status"] == "declined" and b["declined_reason"]
    print("SMOKE 5/7 PASS: Brand authority decline C18")

    # 6. Projection rebuild
    reb = client.post("/v1/admin/projection/rebuild", headers=PLATFORM)
    assert reb.status_code == 200 and reb.json()["counts"]["tickets"] > 0
    print("SMOKE 6/7 PASS: Projection rebuild")

    # 7. Dashboard overview query
    ov = client.get("/v1/centre/overview", headers=CONSOLE_FW)
    assert ov.status_code == 200 and "fvr_14d" in ov.json()
    print(f"SMOKE 7/7 PASS: Dashboard overview (fvr_14d={ov.json()['fvr_14d']}) [target={base_url or 'in-process'}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_smoke())
