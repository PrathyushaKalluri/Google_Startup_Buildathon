"""Check your .env before recording.
  python check_setup.py                 -> checks keys and lists models your LLM key can use
  python check_setup.py path/to/clip.ogg -> ALSO makes ONE real Gnani call (uses 1 credit)"""
import sys, json
from circuit import db, llm, gnani

ok = True
print("LLM_PROVIDER:", llm.provider() or "MISSING", "| LLM_MODEL:", llm.model_id() or "MISSING")
try:
    models = llm.list_models()
    print(f"Your key can use {len(models)} models, e.g.:", ", ".join(models[:12]))
    if llm.model_id() and llm.model_id() not in models:
        print("!! LLM_MODEL is not in that list. Copy one exactly."); ok = False
except Exception as e:
    print("!! Could not list models:", e); ok = False
if llm.model_id():
    try:
        d, raw = llm.complete('Reply with JSON {"ok": true}', "ping")
        print("LLM test call:", d)
    except Exception as e:
        print("!! LLM test call failed:", e); ok = False
print("GNANI_STT_API_KEY set:", bool(db.env("GNANI_STT_API_KEY")), "| language:", db.env("GNANI_LANGUAGE_CODE", "te-IN"))
if len(sys.argv) > 1:
    p = sys.argv[1]
    print("Audio seconds:", gnani.audio_seconds(p))
    r = gnani.transcribe("SETUP-PROBE", p, p.split("/")[-1], None)
    print("Gnani HTTP", r["http_status"], "| blocked:", r["blocked_reason"])
    print("Raw response:", r["raw_text"])
print("\nALL GOOD" if ok else "\nFix the lines marked !! above")
