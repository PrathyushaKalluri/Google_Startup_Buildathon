"""One configured LLM (Claude OR Gemini). Returns a parsed JSON decision dict."""
import json
import re
import httpx
from . import db


class LLMError(Exception):
    pass


def provider():
    return db.env("LLM_PROVIDER", "").lower()


def model_id():
    return db.env("LLM_MODEL", "")


def _parse_json(text):
    text = text.strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.M).strip()
    try:
        return json.loads(text)
    except Exception:
        m = re.search(r"\{.*\}", text, re.S)
        if m:
            return json.loads(m.group(0))
        raise LLMError("Model did not return JSON: " + text[:300])


def complete(system, user, transport=None):
    """Returns (decision_dict, raw_text)."""
    p, m = provider(), model_id()
    if p not in ("claude", "anthropic", "gemini"):
        raise LLMError("Set LLM_PROVIDER=claude or LLM_PROVIDER=gemini in .env")
    if not m:
        raise LLMError("Set LLM_MODEL in .env (run `python check_setup.py` to list models your key can use)")
    h = transport or httpx
    if p in ("claude", "anthropic"):
        key = db.env("ANTHROPIC_API_KEY")
        if not key:
            raise LLMError("ANTHROPIC_API_KEY missing in .env")
        r = h.post("https://api.anthropic.com/v1/messages",
                   headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                            "content-type": "application/json"},
                   json={"model": m, "max_tokens": 1500, "system": system,
                         "messages": [{"role": "user", "content": user}]}, timeout=120)
        if r.status_code != 200:
            raise LLMError(f"Anthropic HTTP {r.status_code}: {r.text[:400]}")
        raw = "".join(b.get("text", "") for b in r.json().get("content", []))
    else:
        key = db.env("GEMINI_API_KEY")
        if not key:
            raise LLMError("GEMINI_API_KEY missing in .env")
        r = h.post(f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent",
                   headers={"x-goog-api-key": key, "content-type": "application/json"},
                   json={"system_instruction": {"parts": [{"text": system}]},
                         "contents": [{"role": "user", "parts": [{"text": user}]}],
                         "generationConfig": {"responseMimeType": "application/json",
                                              "temperature": 0.2}}, timeout=120)
        if r.status_code != 200:
            raise LLMError(f"Gemini HTTP {r.status_code}: {r.text[:400]}")
        cands = r.json().get("candidates", [])
        raw = "".join(pt.get("text", "") for c in cands for pt in c.get("content", {}).get("parts", []))
    return _parse_json(raw), raw


def list_models():
    p = provider()
    if p in ("claude", "anthropic"):
        r = httpx.get("https://api.anthropic.com/v1/models",
                      headers={"x-api-key": db.env("ANTHROPIC_API_KEY"), "anthropic-version": "2023-06-01"},
                      timeout=30)
        r.raise_for_status()
        return [d["id"] for d in r.json().get("data", [])]
    r = httpx.get("https://generativelanguage.googleapis.com/v1beta/models",
                  headers={"x-goog-api-key": db.env("GEMINI_API_KEY")}, timeout=30)
    r.raise_for_status()
    return [d["name"].split("/")[-1] for d in r.json().get("models", [])
            if "generateContent" in d.get("supportedGenerationMethods", [])]
