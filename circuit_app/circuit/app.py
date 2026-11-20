"""Circuit demo server. Run: python run.py  ->  http://localhost:8000"""
import json
import uuid
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, JSONResponse
from . import db, seed, worker, llm
from .ui import CONSOLE_HTML, TRACE_HTML

app = FastAPI(title="Circuit")
AUDIO_DIR = db.ROOT / "data" / "audio"


@app.on_event("startup")
def _startup():
    n = seed.seed_all()
    print(f"[circuit] knowledge chunks indexed: {n}")
    if db.env("CIRCUIT_NO_WORKER") != "1":
        worker.start()


def _case_or_new():
    cid = db.active_case()
    if not cid:
        cid = db.new_case(seed.new_case_facts())
        db.log_event(cid, "case_opened", "circuit", "S1 case opened by first household event", "SYSTEM",
                     {"agency": seed.AGENCY["name"], "fixtures": "SYNTHETIC_FIXTURE"}, state_after="S1")
    return cid


def _need_case():
    cid = db.active_case()
    if not cid:
        raise HTTPException(400, "No active case. The household must send a voice note or message first.")
    return cid


def _actor(cid, role, kind, summary, payload=None, run_agent=True):
    eid = db.log_event(cid, kind, role, summary, "ROLEPLAY", payload, transport="ROLEPLAY_INBOX")
    if run_agent:
        db.enqueue(cid, "agent", eid)
    return {"ok": True, "event_id": eid}


# ---------- household ----------
@app.post("/api/household/audio")
async def household_audio(file: UploadFile = File(...)):
    cid = _case_or_new()
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    ext = (file.filename or "note.ogg").rsplit(".", 1)[-1][:5]
    path = AUDIO_DIR / f"{cid}-{uuid.uuid4().hex[:6]}.{ext}"
    path.write_bytes(await file.read())
    eid = db.log_event(cid, "household_audio", "household", f"Voice note received: {file.filename}", "ROLEPLAY",
                       {"path": str(path), "filename": file.filename, "mime": file.content_type},
                       transport="ROLEPLAY_INBOX (file upload)")
    db.enqueue(cid, "stt", eid)
    return {"ok": True, "case_id": cid, "status": "AWAITING_STT"}


@app.post("/api/household/text")
def household_text(text: str = Form(...)):
    cid = _case_or_new()
    return _actor(cid, "household", "household_text", text, {"text": text})


@app.post("/api/household/slot")
def household_slot(slot: str = Form(...)):
    cid = _need_case()
    f = db.get_case(cid)["facts"]
    if slot not in f["slots_offered"]:
        raise HTTPException(400, "That slot was not offered.")
    f["slot_selected"] = slot
    db.save_facts(cid, f)
    return _actor(cid, "household", "household_slot_choice", f"Household chose slot {slot}", {"slot": slot})


@app.post("/api/household/access")
def household_access():
    cid = _need_case()
    f = db.get_case(cid)["facts"]
    f["resident"]["access_permission"] = "GRANTED"
    db.save_facts(cid, f)
    return _actor(cid, "household", "resident_access_granted", "Resident (adult) grants home access for the chosen slot")


# ---------- agency ----------
@app.post("/api/agency/assign")
def agency_assign(tech_id: str = Form(...)):
    cid = _need_case()
    f = db.get_case(cid)["facts"]
    if tech_id not in [t["tech_id"] for t in seed.TECHS]:
        raise HTTPException(400, "Unknown technician")
    f["assigned_tech"], f["tech_accepted"] = tech_id, False
    db.save_facts(cid, f)
    return _actor(cid, "agency", "agency_assignment", f"Agency dispatcher assigned {tech_id}", {"tech_id": tech_id})


@app.post("/api/agency/signoff")
def agency_signoff():
    cid = _need_case()
    f = db.get_case(cid)["facts"]
    f["owner_signoff"] = True
    db.save_facts(cid, f)
    return _actor(cid, "agency", "owner_signoff", "Agency owner signs off READY (pilot L2 gate)")


@app.post("/api/agency/text")
def agency_text(text: str = Form(...)):
    return _actor(_need_case(), "agency", "agency_text", text, {"text": text})


# ---------- technician ----------
@app.post("/api/technician/accept")
def tech_accept():
    cid = _need_case()
    f = db.get_case(cid)["facts"]
    if not f["assigned_tech"]:
        raise HTTPException(400, "No job assigned yet")
    f["tech_accepted"] = True
    db.save_facts(cid, f)
    return _actor(cid, "technician", "technician_accept", f"{f['assigned_tech']} accepted the job")


@app.post("/api/technician/decline")
def tech_decline():
    cid = _need_case()
    f = db.get_case(cid)["facts"]
    t = f["assigned_tech"]
    f["assigned_tech"], f["tech_accepted"], f["slots_offered"], f["slot_selected"] = None, False, [], None
    db.save_facts(cid, f)
    return _actor(cid, "technician", "technician_decline", f"{t} declined the job")


@app.post("/api/technician/kit")
def tech_kit():
    cid = _need_case()
    f = db.get_case(cid)["facts"]
    if not f["kit"]["sku"]:
        raise HTTPException(400, "No compatible kit identified by Circuit yet")
    f["kit"]["custody_ack"] = True
    db.save_facts(cid, f)
    return _actor(cid, "technician", "kit_custody_ack", f"Technician confirms {f['kit']['sku']} is in the bag (role-play prop)")


@app.post("/api/technician/text")
def tech_text(text: str = Form(...)):
    return _actor(_need_case(), "technician", "technician_text", text, {"text": text})


# ---------- payer ----------
@app.post("/api/payer/approve")
def payer_approve():
    cid = _need_case()
    f = db.get_case(cid)["facts"]
    if not f["quote"]:
        raise HTTPException(400, "No authorization request yet")
    f["payer_approved"], f["payer_approved_ceiling_paise"] = True, f["quote"]["ceiling_paise"]
    db.save_facts(cid, f)
    return _actor(cid, "payer", "payer_approval",
                  f"Payer approves ceiling Rs {f['quote']['ceiling_paise'] / 100:.0f} in UPI app (role-play)")


@app.post("/api/payer/text")
def payer_text(text: str = Form(...)):
    return _actor(_need_case(), "payer", "payer_text", text, {"text": text})


# ---------- wizard (doc-simulated partner responses) ----------
@app.post("/api/wizard/{pid}")
def wizard(pid: str, response: str = Form(...), doc_section: str = Form("")):
    p = db.q("SELECT * FROM pending_sim WHERE id=?", (pid,), one=True)
    if not p:
        raise HTTPException(404, "Unknown pending request")
    try:
        js = json.loads(response)
    except Exception:
        raise HTTPException(400, "Paste valid JSON copied from the partner documentation")
    cid = p["case_id"]
    f = db.get_case(cid)["facts"]
    if p["rail"] == "PINE_LABS":
        st = str(js.get("status", "")).upper() or "UNKNOWN"
        f["pine"]["status"] = st
        kind = "pine_response"
    else:
        f["route"]["status"] = "ERROR" if "error" in js else "RESPONDED"
        kind = "delhivery_response"
    db.save_facts(cid, f)
    db.x("UPDATE pending_sim SET status='RESPONDED', response=?, responded_at=? WHERE id=?",
         (response, db.now(), pid))
    eid = db.log_event(cid, kind, "wizard", f"{p['rail']} documented response pasted for {pid}", "DOC_SIMULATED",
                       {"request": json.loads(p["request"]), "response_doc_shaped": js,
                        "doc_ref": doc_section or p["doc_ref"]}, transport="WIZARD (teammate)")
    db.enqueue(cid, "agent", eid)
    return {"ok": True}


# ---------- state / trace ----------
@app.post("/api/reset")
def reset():
    db.x("UPDATE cases SET status='CLOSED_DEMO_RESET' WHERE status='ACTIVE'")
    return {"ok": True}


@app.get("/api/state")
def state():
    cid = db.active_case()
    if not cid:
        return {"case": None}
    c = db.get_case(cid)
    out = {r["to_role"]: [] for r in db.q("SELECT DISTINCT to_role FROM outbox WHERE case_id=?", (cid,))}
    for r in db.q("SELECT * FROM outbox WHERE case_id=? ORDER BY id", (cid,)):
        out[r["to_role"]].append({"ts": r["ts"], "text": r["text"]})
    pend = [dict(r) for r in db.q("SELECT * FROM pending_sim WHERE case_id=? ORDER BY created_at", (cid,))]
    busy = db.q("SELECT COUNT(*) c FROM jobs WHERE case_id=? AND status IN ('QUEUED','RUNNING')", (cid,), one=True)["c"]
    err = db.q("SELECT summary, ts FROM events WHERE case_id=? AND kind='agent_error' ORDER BY id DESC LIMIT 1", (cid,), one=True)
    return {"case": {"id": cid, "state": c["state"], "facts": c["facts"]}, "outbox": out, "pending": pend,
            "last_error": dict(err) if err else None,
            "techs": seed.TECHS, "busy": busy, "model": f"{llm.provider()}:{llm.model_id()}"}


@app.get("/api/trace/{cid}")
def trace_json(cid: str):
    c = db.get_case(cid)
    if not c:
        raise HTTPException(404)
    return {"case": c, "events": db.events(cid)}


@app.get("/trace/{cid}", response_class=HTMLResponse)
def trace_page(cid: str):
    return TRACE_HTML.replace("__CID__", cid)


@app.get("/", response_class=HTMLResponse)
def console():
    return CONSOLE_HTML


@app.get("/export/{cid}.md", response_class=PlainTextResponse)
def export(cid: str):
    """Round 3 Part 1 decision log, generated from the real run."""
    evs = db.events(cid)
    lines = [f"# Circuit decision log - {cid}", "",
             f"Model: {llm.provider()}:{llm.model_id()}  |  System prompt: 04_RUNTIME_SYSTEM_PROMPT.md v0.6", "",
             "| # | When | What the agent received | Where it came from | What it decided | Why (rule) | What it did or said, to whom | Through |",
             "|---|---|---|---|---|---|---|---|"]
    last_input = ("(start)", "")
    n = 0
    for i, e in enumerate(evs):
        if e["kind"] != "agent_decision":
            if e["actor"] != "circuit":
                last_input = (e["summary"].replace("|", "/")[:120], f"{e['transport'] or e['kind']} ({e['source_mode']})")
            continue
        n += 1
        p = e["payload"] or {}
        chosen = p.get("chosen", "")
        did, via = chosen, "Circuit backend"
        nxt = evs[i + 1] if i + 1 < len(evs) else None
        if chosen == "respond":
            outs = [x for x in evs[i + 1:i + 6] if x["kind"] == "message_out"]
            did = "; ".join(f"to {o['payload']['to_role']}: \"{o['payload']['text']}\"" for o in outs) or "waited (no message)"
            via = "ROLEPLAY_INBOX"
        elif nxt is not None:
            did = f"{chosen} -> {nxt['summary'][:140]}"
            via = {"pine_request": "Pine Labs (DOC_SIMULATED)", "delhivery_request": "Delhivery Maps (DOC_SIMULATED)"}.get(nxt["kind"], "internal tool")
        lines.append(f"| {n} | {e['ts']} | {last_input[0]} | {last_input[1]} | {e['summary'].replace('|', '/')} | "
                     f"{e['rule_ids']} | {did.replace('|', '/')} | {via} |")
    lines += ["", "## Partner calls (exact request/response)", ""]
    for e in evs:
        if e["kind"] in ("gnani_stt", "pine_request", "pine_response", "delhivery_request", "delhivery_response"):
            lines += [f"### {e['kind']} - {e['ts']} ({e['source_mode']})", "```json",
                      json.dumps(e["payload"], indent=1, ensure_ascii=False, default=str)[:6000], "```", ""]
    return "\n".join(lines)


@app.get("/health")
def health():
    return {"ok": True}
