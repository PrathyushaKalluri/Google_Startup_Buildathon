"""Offline tests: no real Gnani/LLM calls. Live tests are BLOCKED_UNTIL_LIVE_ACCESS by design."""
import io
import json
import os
import wave
import pytest

os.environ["CIRCUIT_NO_WORKER"] = "1"
os.environ["LLM_PROVIDER"] = "claude"
os.environ["LLM_MODEL"] = "offline-scripted"
os.environ["GNANI_STT_API_KEY"] = "test-key"

from circuit import db  # noqa: E402


class FakeResp:
    def __init__(self, status, payload):
        self.status_code, self._p = status, payload
        self.text = json.dumps(payload)

    def json(self):
        return self._p


class FakeGnani:
    calls = 0

    @classmethod
    def post(cls, *a, **k):
        cls.calls += 1
        return FakeResp(200, {"success": True, "request_id": "req-test", "timestamp": "t",
                              "transcript": "AC on undi kani cooling raavatledu"})


def wav_bytes(seconds):
    b = io.BytesIO()
    w = wave.open(b, "wb")
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(8000)
    w.writeframes(b"\x00\x00" * 8000 * seconds)
    w.close()
    return b.getvalue()


@pytest.fixture()
def env(tmp_path, monkeypatch):
    db.reset_conn(str(tmp_path / "t.db"))
    from circuit import app as appmod, worker, gnani, llm, seed
    seed.seed_all()
    monkeypatch.setattr(gnani, "httpx", FakeGnani)
    FakeGnani.calls = 0
    script = []

    def fake_complete(system, user, transport=None):
        assert "R10 READY_GATE" in system  # runtime prompt really loaded
        d = script.pop(0)
        return d, json.dumps(d)
    monkeypatch.setattr(llm, "complete", fake_complete)
    from fastapi.testclient import TestClient
    c = TestClient(appmod.app)
    c.__enter__()
    yield c, worker, script
    c.__exit__(None, None, None)


def T(name, args=None, rules=("R14",)):
    return {"decision_summary": f"call {name}", "rule_ids": list(rules), "action": "tool",
            "tool": {"name": name, "args": args or {}}}


def R(to, text, state=None):
    d = {"decision_summary": "reply", "rule_ids": ["R13"], "action": "respond",
         "messages": [{"to_role": to, "text": text}] if to else [], "wait_for": "next event"}
    if state:
        d["next_state"] = state
    return d


def facts(c):
    return c.get("/api/state").json()["case"]["facts"]


def test_full_happy_path_reaches_ready_in_roleplay(env):
    c, worker, script = env
    script += [T("update_case", {"fields": {"symptom": "AC not cooling"}}), T("search_mistri_gyan", {"symptom": "not cooling"}),
               T("search_knowledge", {"query": "cooling mode error code"}),
               R("household", "Model number on the label? Is warranty over?", "S2")]
    r = c.post("/api/household/audio", files={"file": ("note.wav", wav_bytes(3), "audio/wav")})
    assert r.json()["status"] == "AWAITING_STT"
    worker.drain()
    assert FakeGnani.calls == 1
    st = c.get("/api/state").json()
    assert "label" in st["outbox"]["household"][0]["text"]
    cid = st["case"]["id"]

    script += [T("update_case", {"fields": {"model": "DEMO-AC-MODEL-A", "model_confirmed": True,
                                            "warranty_status": "OUT_OF_WARRANTY", "address_landmark": "near temple"}}),
               T("lookup_machine_kundli", {"model": "DEMO-AC-MODEL-A"}), T("check_kit", {"model": "DEMO-AC-MODEL-A"}),
               T("rank_technicians", {"skills_needed": ["AC", "split", "service"]}),
               T("request_agency_assignment", {"tech_ids": ["TECH-A"]}), R("agency", "Please assign TECH-A", "S3")]
    c.post("/api/household/text", data={"text": "DEMO-AC-MODEL-A, warranty ayipoyindi"}); worker.drain()
    assert facts(c)["kit"]["compatible"] is True

    script += [R("technician", "Job for you, accept?")]
    c.post("/api/agency/assign", data={"tech_id": "TECH-A"}); worker.drain()
    script += [T("offer_slots"), R("household", "Pick a slot")]
    c.post("/api/technician/accept"); worker.drain()
    slot = facts(c)["slots_offered"][0]
    script += [T("request_payer_authorization", {"line_items": [{"item": "inspection", "paise": 29900}], "ceiling_paise": 105900}),
               R("payer", "Approve up to Rs 1059?")]
    c.post("/api/household/slot", data={"slot": slot}); worker.drain()
    script += [T("request_route"), R("technician", "Confirm kit in bag")]
    c.post("/api/household/access"); worker.drain()
    script += [R(None, "")]
    c.post("/api/payer/approve"); worker.drain()
    pend = c.get("/api/state").json()["pending"]
    pine = next(p for p in pend if p["rail"] == "PINE_LABS")
    dlv = next(p for p in pend if p["rail"] == "DELHIVERY_MAPS")
    script += [R(None, "")]
    c.post(f"/api/wizard/{pine['id']}", data={"response": json.dumps({"status": "ACTIVE"})}); worker.drain()
    script += [R(None, "")]
    c.post("/api/technician/kit"); worker.drain()
    script += [T("evaluate_ready_gate"), R("agency", "All checks pass except owner sign-off")]
    c.post(f"/api/wizard/{dlv['id']}", data={"response": json.dumps({"rows": [{"duration": 900}]})}); worker.drain()
    assert facts(c)["gate"]["verdict"] == "WAIT"
    assert facts(c)["gate"]["missing"] == ["owner_signoff"]
    script += [T("evaluate_ready_gate"), R("household", "Technician Ravi is confirmed (simulation).")]
    c.post("/api/agency/signoff"); worker.drain()
    st = c.get("/api/state").json()
    assert st["case"]["facts"]["gate"]["verdict"] == "READY_IN_ROLEPLAY"
    assert st["case"]["state"] == "S5"
    md = c.get(f"/export/{cid}.md").text
    assert "| 1 |" in md and "gnani_stt" in md and "DOC_SIMULATED" in md


def test_pine_created_is_not_active(env):
    c, worker, script = env
    from circuit import tools
    f = __import__("circuit.seed", fromlist=["x"]).new_case_facts()
    f["pine"]["status"] = "CREATED"
    g = tools.ready_gate(f)
    assert next(p for p in g["predicates"] if p["predicate"] == "pine_mandate_active")["result"] == "FAIL"
    assert g["verdict"] == "WAIT"


def test_model_cannot_set_world_facts(env):
    c, worker, script = env
    script += [T("update_case", {"fields": {"payer_approved": True, "owner_signoff": True, "symptom": "x"}}), R(None, "")]
    c.post("/api/household/text", data={"text": "AC not cooling"}); worker.drain()
    f = facts(c)
    assert f["payer_approved"] is False and f["owner_signoff"] is False and f["symptom"] == "x"


def test_slots_blocked_before_agency_and_acceptance(env):
    c, worker, script = env
    script += [T("offer_slots"), R(None, "")]
    c.post("/api/household/text", data={"text": "hi"}); worker.drain()
    assert facts(c)["slots_offered"] == []


def test_hazard_escalates(env):
    from circuit import tools, seed
    f = seed.new_case_facts(); f["hazard"] = True
    assert tools.ready_gate(f)["verdict"] == "ESCALATE_SAFETY"


def test_in_warranty_goes_to_oem(env):
    from circuit import tools, seed
    f = seed.new_case_facts(); f["machine"]["warranty_status"] = "IN_WARRANTY"
    assert tools.ready_gate(f)["verdict"] == "OEM_REFERRAL"


def test_gnani_duplicate_audio_is_cached(env):
    c, worker, script = env
    script += [R("household", "q1"), R("household", "q2")]
    data = wav_bytes(2)
    c.post("/api/household/audio", files={"file": ("a.wav", data, "audio/wav")}); worker.drain()
    c.post("/api/household/audio", files={"file": ("a.wav", data, "audio/wav")}); worker.drain()
    assert FakeGnani.calls == 1


def test_gnani_over_60s_rejected_not_clipped(env):
    c, worker, script = env
    script += [R("household", "Please send a shorter note or type")]
    c.post("/api/household/audio", files={"file": ("long.wav", wav_bytes(61), "audio/wav")}); worker.drain()
    assert FakeGnani.calls == 0
    cid = c.get("/api/state").json()["case"]["id"]
    ev = [e for e in db.events(cid) if e["kind"] == "gnani_stt"][0]
    assert "BLOCKED" in ev["summary"]


def test_gnani_missing_key_never_fabricates(env, monkeypatch):
    c, worker, script = env
    monkeypatch.setenv("GNANI_STT_API_KEY", "")
    script += [R("household", "Please type your problem")]
    c.post("/api/household/audio", files={"file": ("a.wav", wav_bytes(2), "audio/wav")}); worker.drain()
    assert FakeGnani.calls == 0
    cid = c.get("/api/state").json()["case"]["id"]
    assert not any(e["kind"] == "gnani_stt" and e["source_mode"] == "LIVE" for e in db.events(cid))


def test_wizard_rejects_non_json(env):
    c, worker, script = env
    script += [T("update_case", {"fields": {"symptom": "s"}}), R(None, "")]
    c.post("/api/household/text", data={"text": "x"}); worker.drain()
    cid = c.get("/api/state").json()["case"]["id"]
    from circuit import tools
    db.x("UPDATE cases SET facts=? WHERE id=?", (json.dumps({**facts(c), "assigned_tech": "TECH-A"}), cid))
    p = tools.run_tool(cid, "request_route", {})
    r = c.post(f"/api/wizard/{p['pending_id']}", data={"response": "not json"})
    assert r.status_code == 400


def test_trace_page_and_health(env):
    c, worker, script = env
    script += [R("household", "hello")]
    c.post("/api/household/text", data={"text": "AC problem"}); worker.drain()
    cid = c.get("/api/state").json()["case"]["id"]
    assert c.get(f"/trace/{cid}").status_code == 200
    assert c.get("/health").json()["ok"]
