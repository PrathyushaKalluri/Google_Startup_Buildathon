"""Durable SQLite job worker (survives restarts: QUEUED/RUNNING jobs are picked up again)."""
import json
import threading
import time
import traceback
from . import db, agent, gnani

_stop = threading.Event()


def process(job):
    ev = db.q("SELECT * FROM events WHERE id=?", (job["event_id"],), one=True)
    payload = json.loads(ev["payload"]) if ev and ev["payload"] else {}
    cid = job["case_id"]
    if job["kind"] == "stt":
        res = gnani.transcribe(cid, payload["path"], payload["filename"], payload.get("mime"))
        case = db.get_case(cid)
        f = case["facts"]
        f["gnani_calls"] = f.get("gnani_calls", 0) + (0 if res.get("cached") or res["http_status"] is None else 1)
        db.save_facts(cid, f)
        raw = res["raw_text"]
        try:
            raw_view = json.loads(raw) if raw else None
        except Exception:
            raw_view = raw
        if res["ok"]:
            summary = f"Gnani transcript: {res['transcript']}" + (" (cached, no new call)" if res.get("cached") else "")
            eid = db.log_event(cid, "gnani_stt", "gnani", summary, "LIVE",
                               {"request": res["request_meta"], "http_status": res["http_status"],
                                "response_unaltered": raw_view}, transport="HTTPS api.vachana.ai")
            trig = {"kind": "household_voice_transcribed", "transcript": res["transcript"],
                    "source": "Gnani STT (LIVE) of household voice note (ROLEPLAY speaker)"}
        else:
            eid = db.log_event(cid, "gnani_stt", "gnani", f"BLOCKED/FAILED: {res['blocked_reason']}",
                               "LIVE" if res["http_status"] else "SYSTEM",
                               {"request": res["request_meta"], "http_status": res["http_status"],
                                "response_unaltered": raw_view, "blocked_reason": res["blocked_reason"]})
            trig = {"kind": "voice_note_not_transcribed", "reason": res["blocked_reason"],
                    "instruction": "Do not guess the complaint. Ask the household to type it or re-record shorter."}
        agent.run(cid, trig)
    elif job["kind"] == "agent":
        agent.run(cid, {"kind": ev["kind"], "actor": ev["actor"], "summary": ev["summary"],
                        "source_mode": ev["source_mode"], "payload": payload})


def loop():
    db.x("UPDATE jobs SET status='QUEUED' WHERE status='RUNNING'")  # recover after restart
    while not _stop.is_set():
        job = db.q("SELECT * FROM jobs WHERE status='QUEUED' ORDER BY id LIMIT 1", one=True)
        if not job:
            time.sleep(0.4)
            continue
        db.x("UPDATE jobs SET status='RUNNING' WHERE id=?", (job["id"],))
        try:
            process(job)
            db.x("UPDATE jobs SET status='DONE' WHERE id=?", (job["id"],))
        except Exception as e:
            db.x("UPDATE jobs SET status='FAILED', error=? WHERE id=?", (traceback.format_exc()[-1500:], job["id"]))
            db.log_event(job["case_id"], "agent_error", "circuit", f"Job failed: {e!r}", "SYSTEM")


def start():
    t = threading.Thread(target=loop, daemon=True)
    t.start()
    return t


def drain(timeout=30):
    """Test helper: process queued jobs synchronously."""
    end = time.time() + timeout
    while time.time() < end:
        job = db.q("SELECT * FROM jobs WHERE status='QUEUED' ORDER BY id LIMIT 1", one=True)
        if not job:
            return
        db.x("UPDATE jobs SET status='RUNNING' WHERE id=?", (job["id"],))
        process(job)
        db.x("UPDATE jobs SET status='DONE' WHERE id=?", (job["id"],))
