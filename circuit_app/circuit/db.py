"""Config + SQLite storage. One file DB, durable job table, FTS5 knowledge index."""
import json
import os
import sqlite3
import threading
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IST = timezone(timedelta(hours=5, minutes=30))


def load_env():
    """Tiny .env loader (no extra dependency). Real env vars win."""
    p = ROOT / ".env"
    if p.exists():
        for line in p.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


load_env()


def env(name, default=""):
    return os.environ.get(name, default)


def now():
    return datetime.now(IST).isoformat(timespec="seconds")


DB_PATH = env("CIRCUIT_DB_PATH", str(ROOT / "data" / "circuit.db"))
_lock = threading.RLock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS cases(
  id TEXT PRIMARY KEY, agency_id TEXT, state TEXT, status TEXT,
  created_at TEXT, facts TEXT);
CREATE TABLE IF NOT EXISTS events(
  id INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT, ts TEXT, kind TEXT,
  actor TEXT, source_mode TEXT, transport TEXT, summary TEXT, rule_ids TEXT,
  state_before TEXT, state_after TEXT, model_id TEXT, payload TEXT);
CREATE TABLE IF NOT EXISTS jobs(
  id INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT, kind TEXT, event_id INTEGER,
  status TEXT, created_at TEXT, error TEXT);
CREATE TABLE IF NOT EXISTS pending_sim(
  id TEXT PRIMARY KEY, case_id TEXT, rail TEXT, request TEXT, doc_ref TEXT,
  status TEXT, response TEXT, created_at TEXT, responded_at TEXT);
CREATE TABLE IF NOT EXISTS outbox(
  id INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT, ts TEXT, to_role TEXT,
  channel TEXT, text TEXT, status TEXT);
CREATE TABLE IF NOT EXISTS gnani_calls(
  id INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT, sha256 TEXT, ts TEXT,
  http_status INTEGER, response_text TEXT);
CREATE TABLE IF NOT EXISTS machines(
  model TEXT PRIMARY KEY, record TEXT);
CREATE TABLE IF NOT EXISTS faults(
  fault_id TEXT PRIMARY KEY, record TEXT);
CREATE VIRTUAL TABLE IF NOT EXISTS kb USING fts5(chunk_id, source_id, title, text, provenance);
"""


def connect():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c


_conn = None


def conn():
    global _conn
    if _conn is None:
        _conn = connect()
        _conn.executescript(SCHEMA)
        _conn.commit()
    return _conn


def reset_conn(path=None):
    """Used by tests to point at a fresh DB."""
    global _conn, DB_PATH
    if _conn is not None:
        _conn.close()
    _conn = None
    if path:
        DB_PATH = path


def q(sql, args=(), one=False):
    with _lock:
        cur = conn().execute(sql, args)
        rows = cur.fetchall()
    return (rows[0] if rows else None) if one else rows


def x(sql, args=()):
    with _lock:
        cur = conn().execute(sql, args)
        conn().commit()
        return cur.lastrowid


# ---------- cases ----------

def new_case(facts):
    cid = "CASE-" + uuid.uuid4().hex[:6].upper()
    x("INSERT INTO cases VALUES(?,?,?,?,?,?)",
      (cid, "AGENCY-DEMO-01", "S1", "ACTIVE", now(), json.dumps(facts)))
    return cid


def get_case(cid):
    r = q("SELECT * FROM cases WHERE id=?", (cid,), one=True)
    if not r:
        return None
    d = dict(r)
    d["facts"] = json.loads(d["facts"])
    return d


def save_facts(cid, facts):
    x("UPDATE cases SET facts=? WHERE id=?", (json.dumps(facts), cid))


def set_state(cid, state):
    x("UPDATE cases SET state=? WHERE id=?", (state, cid))


def active_case():
    r = q("SELECT id FROM cases WHERE status='ACTIVE' ORDER BY created_at DESC LIMIT 1", one=True)
    return r["id"] if r else None


# ---------- events ----------

def log_event(case_id, kind, actor, summary, source_mode, payload=None, transport="",
              rule_ids=None, state_before="", state_after="", model_id=""):
    return x("""INSERT INTO events(case_id,ts,kind,actor,source_mode,transport,summary,rule_ids,
             state_before,state_after,model_id,payload) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
             (case_id, now(), kind, actor, source_mode, transport, summary,
              ",".join(rule_ids or []), state_before, state_after, model_id,
              json.dumps(payload, ensure_ascii=False, default=str) if payload is not None else ""))


def events(case_id):
    out = []
    for r in q("SELECT * FROM events WHERE case_id=? ORDER BY id", (case_id,)):
        d = dict(r)
        try:
            d["payload"] = json.loads(d["payload"]) if d["payload"] else None
        except Exception:
            pass
        out.append(d)
    return out


def enqueue(case_id, kind, event_id):
    return x("INSERT INTO jobs(case_id,kind,event_id,status,created_at) VALUES(?,?,?,?,?)",
             (case_id, kind, event_id, "QUEUED", now()))
