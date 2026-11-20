"""Gnani (Vachana) speech-to-text. LIVE only: never fabricates a transcript."""
import hashlib
import httpx
from . import db

URL = "https://api.vachana.ai/stt/v3"


def audio_seconds(path):
    try:
        import mutagen
        f = mutagen.File(path)
        if f is not None and f.info and getattr(f.info, "length", None):
            return float(f.info.length)
    except Exception:
        pass
    return None


def _extract_transcript(js):
    if not isinstance(js, dict):
        return None
    for k in ("transcript", "text"):
        if isinstance(js.get(k), str) and js[k].strip():
            return js[k]
    for k in ("data", "result", "results"):
        v = js.get(k)
        if isinstance(v, dict):
            t = _extract_transcript(v)
            if t:
                return t
        if isinstance(v, list) and v and isinstance(v[0], dict):
            t = _extract_transcript(v[0])
            if t:
                return t
    return None


def transcribe(case_id, path, filename, mime, transport=None):
    """Returns dict(ok, transcript, http_status, raw_text, request_meta, blocked_reason)."""
    key = db.env("GNANI_STT_API_KEY")
    lang = db.env("GNANI_LANGUAGE_CODE", "te-IN")
    max_s = float(db.env("GNANI_REST_MAX_SECONDS", "60"))
    per_case = int(db.env("GNANI_MAX_PER_CASE", "2"))
    demo_max = int(db.env("GNANI_DEMO_MAX_STT_CALLS", "6"))
    data = open(path, "rb").read()
    digest = hashlib.sha256(data).hexdigest()
    secs = audio_seconds(path)
    req_meta = {"method": "POST", "url": URL, "headers": {"X-API-Key-ID": "***redacted***"},
                "multipart": {"audio_file": f"{filename} ({len(data)} bytes, {mime})",
                              "language_code": lang},
                "audio_sha256": digest, "audio_seconds_measured": secs}

    cached = db.q("SELECT * FROM gnani_calls WHERE sha256=? AND http_status=200 ORDER BY id DESC LIMIT 1",
                  (digest,), one=True)
    if cached:
        import json
        raw = cached["response_text"]
        try:
            t = _extract_transcript(json.loads(raw))
        except Exception:
            t = None
        return {"ok": bool(t), "transcript": t, "http_status": 200, "raw_text": raw,
                "request_meta": req_meta, "cached": True, "blocked_reason": None}

    def blocked(reason):
        return {"ok": False, "transcript": None, "http_status": None, "raw_text": None,
                "request_meta": req_meta, "blocked_reason": reason}

    if not key:
        return blocked("GNANI_STT_API_KEY not set in .env")
    if secs is not None and secs > max_s:
        return blocked(f"Clip is {secs:.0f}s; Gnani REST limit is {max_s:.0f}s. Ask to re-record shorter (never clipped silently).")
    total = db.q("SELECT COUNT(*) c FROM gnani_calls", one=True)["c"]
    in_case = db.q("SELECT COUNT(*) c FROM gnani_calls WHERE case_id=?", (case_id,), one=True)["c"]
    if total >= demo_max:
        return blocked(f"Internal demo budget reached ({demo_max} Gnani calls). Raise GNANI_DEMO_MAX_STT_CALLS if credits allow.")
    if in_case >= per_case:
        return blocked(f"Internal per-case budget reached ({per_case}). Ask household to type instead.")

    try:
        r = (transport or httpx).post(URL, headers={"X-API-Key-ID": key},
                                      files={"audio_file": (filename, data, mime or "application/octet-stream")},
                                      data={"language_code": lang}, timeout=90)
        status, raw = r.status_code, r.text
    except Exception as e:  # network failure: record, never retry a paid call automatically
        db.x("INSERT INTO gnani_calls(case_id,sha256,ts,http_status,response_text) VALUES(?,?,?,?,?)",
             (case_id, digest, db.now(), -1, repr(e)))
        return blocked(f"Network error calling Gnani: {e!r}")

    db.x("INSERT INTO gnani_calls(case_id,sha256,ts,http_status,response_text) VALUES(?,?,?,?,?)",
         (case_id, digest, db.now(), status, raw))
    t = None
    try:
        t = _extract_transcript(r.json())
    except Exception:
        pass
    reason = None
    if status != 200:
        reason = {403: "403: credits/permission problem", 429: "429: rate limited"}.get(status, f"HTTP {status}")
    elif not t:
        reason = "200 but no transcript field found; see raw response"
    return {"ok": status == 200 and bool(t), "transcript": t, "http_status": status, "raw_text": raw,
            "request_meta": req_meta, "cached": False, "blocked_reason": reason}
