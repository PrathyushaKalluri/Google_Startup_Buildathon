"""Stateful agent loop. Each world event -> the model picks tools/messages until it waits."""
import json
from . import db, llm, tools, seed

MAX_STEPS = int(db.env("AGENT_MAX_STEPS", "8"))
RUNTIME_PROMPT = (db.ROOT / "data" / "04_RUNTIME_SYSTEM_PROMPT.md").read_text()

PROTOCOL = """
## Output protocol (backend-enforced)
You act for: {agency} ({area}). Channel to humans in this demo: ROLEPLAY_INBOX (each role has its own inbox).
Roles you may message: household, payer, agency, technician.
Respond with ONE JSON object only, no prose:
{{"decision_summary": "<one short observable sentence>",
  "rule_ids": ["R03", ...],
  "action": "tool" | "respond",
  "tool": {{"name": "<tool>", "args": {{...}}}},            // when action == tool
  "messages": [{{"to_role": "household", "text": "..."}}],   // when action == respond (may be empty)
  "next_state": "S1".."S5",
  "wait_for": "<which real-world event you now wait for>"}}
Call at most one tool per step; you will see its result and can continue. Finish each turn with action=respond.
Tools: {tools}
Guidance: speak to the household in the language they used (Telugu/Hindi/English, mixed is fine), short messages.
Read back any model number, error code or amount before relying on it. Ask one or two questions at a time.
Typical order: understand symptom+safety -> confirm model (label photo/read-back) + warranty -> search_mistri_gyan/
search_knowledge/lookup_machine_kundli -> rank_technicians + check_kit -> request_agency_assignment -> (after agency
assigns + tech accepts) offer_slots -> request_payer_authorization (+ message payer with itemised amount) and ask
household to grant access -> ask technician to confirm kit in bag -> request_route -> evaluate_ready_gate when facts
change. Ask the agency owner for READY sign-off when everything else passes. Never claim a repair, payment or delivery happened.
"""


def _system():
    t = "\n".join(f"- {k}: {v}" for k, v in tools.TOOL_SPECS.items())
    return RUNTIME_PROMPT + PROTOCOL.format(agency=seed.AGENCY["name"], area=seed.AGENCY["service_area"], tools=t)


def _context(cid, trigger, steps):
    c = db.get_case(cid)
    hist = []
    for e in db.events(cid)[-25:]:
        if e["kind"] in ("agent_decision",):
            continue
        hist.append(f"[{e['ts']}] {e['kind']} ({e['actor']}, {e['source_mode']}): {e['summary']}")
    return json.dumps({
        "case_id": cid, "state": c["state"], "facts": c["facts"],
        "pricing_fixture_paise": seed.PRICES, "triggering_event": trigger,
        "recent_events": hist, "tool_results_this_turn": steps,
    }, ensure_ascii=False, default=str, indent=1)


def run(cid, trigger, transport=None):
    steps = []
    for _ in range(MAX_STEPS):
        before = db.get_case(cid)["state"]
        try:
            d, raw = llm.complete(_system(), _context(cid, trigger, steps), transport=transport)
        except llm.LLMError as e:
            db.log_event(cid, "agent_error", "circuit", str(e), "SYSTEM", state_before=before, state_after=before)
            return
        rules = d.get("rule_ids") or []
        summary = d.get("decision_summary", "")
        nxt = d.get("next_state") or before
        if nxt not in [f"S{i}" for i in range(0, 12)] or nxt in ("S6", "S7", "S8", "S9", "S10", "S11"):
            nxt = before  # model cannot jump to field/proof states in this demo
        if d.get("action") == "tool":
            t = d.get("tool") or {}
            name, args = t.get("name"), t.get("args", {})
            if name not in tools.TOOL_SPECS:
                result = {"error": f"tool {name} not allowlisted"}
            else:
                result = tools.run_tool(cid, name, args)
            after = db.get_case(cid)["state"]
            db.log_event(cid, "agent_decision", "circuit", summary, "MODEL_DECISION",
                         {"chosen": f"tool:{name}", "raw_model_output": raw}, rule_ids=rules,
                         state_before=before, state_after=after, model_id=llm.model_id())
            kind = {"request_payer_authorization": "pine_request", "request_route": "delhivery_request"}.get(name, "tool_call")
            mode = "DOC_SIMULATED" if kind != "tool_call" else (
                "SYNTHETIC_FIXTURE" if name in ("rank_technicians", "check_kit", "lookup_machine_kundli", "search_mistri_gyan") else "SYSTEM")
            db.log_event(cid, kind, "circuit", f"{name} -> {json.dumps(result, ensure_ascii=False, default=str)[:180]}",
                         mode, {"request": {"tool": name, "args": args}, "response": result}, rule_ids=rules)
            steps.append({"tool": name, "args": args, "result": result})
            continue
        # respond
        msgs = d.get("messages") or []
        if nxt != before and db.get_case(cid)["state"] != "S5":
            db.set_state(cid, nxt)
        after = db.get_case(cid)["state"]
        db.log_event(cid, "agent_decision", "circuit", summary, "MODEL_DECISION",
                     {"chosen": "respond", "wait_for": d.get("wait_for"), "raw_model_output": raw},
                     rule_ids=rules, state_before=before, state_after=after, model_id=llm.model_id())
        for m in msgs:
            role = m.get("to_role")
            if role not in ("household", "payer", "agency", "technician"):
                continue
            db.x("INSERT INTO outbox(case_id,ts,to_role,channel,text,status) VALUES(?,?,?,?,?,?)",
                 (cid, db.now(), role, "ROLEPLAY_INBOX", m.get("text", ""), "SHOWN_IN_INBOX"))
            db.log_event(cid, "message_out", "circuit", f"to {role}: {m.get('text', '')}", "MODEL_DECISION",
                         {"to_role": role, "text": m.get("text"), "channel": "ROLEPLAY_INBOX"},
                         transport="ROLEPLAY_INBOX", rule_ids=rules)
        return
    db.log_event(cid, "agent_error", "circuit", f"Stopped after {MAX_STEPS} steps without responding", "SYSTEM")
