"""Orchestrates the whole simulated dataset. Run:  python3 build.py /path/to/out
Output: CSVs (one per table), load.sql, kb/ PDFs, inbox/ (WhatsApp-style messages + media), evaluator_only/ (never shown to the app)."""
import sys, os, json, csv, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
import catalogue, world, people, history, schedule, kb, inbox, safefix, adapt
from stories import STORIES, GROUND_TRUTH

# FK-safe load order. ticket is loaded before reminder (reminder.ticket_id -> ticket); ticket.origin_reminder_id is not seeded.
ORDER = ["brand", "appliance_category", "category_norm", "appliance_model", "rate_card", "kb_document", "coverage_plan", "safe_fix_catalogue", "urgency_rule",
         "service_centre", "centre_commercial", "centre_channel", "centre_brand_authorisation", "centre_capacity", "centre_price", "retailer",
         "technician", "technician_skill", "technician_metrics", "parts_centre", "parts_centre_brand", "part_catalogue", "part_compatibility", "stock",
         "community", "household", "household_member", "household_centre_link", "appliance", "external_ref", "identity_merge", "scoring_config",
         "brand_referral", "retailer_handover", "ticket", "conversation", "urgency_assessment", "consent_gate", "clarifying_qa", "diagnosis_session", "diagnosis_media",
         "fix_attempt", "appliance_event", "visit_plan", "plan_hypothesis", "plan_part", "assignment_candidate", "slot_proposal", "quote", "quote_line", "visit",
         "technician_availability", "visit_media", "visit_part_used", "reservation", "route", "route_stop", "settlement_line", "feedback", "reminder",
         "experience_case", "consent_ledger", "access_log"]

# tables that must stay empty: they are the app's outputs for today's cases and for new work
APP_OUTPUT_TABLES = ["visit_plan", "plan_hypothesis", "plan_part", "assignment_candidate", "slot_proposal", "visit_media", "access_log", "identity_merge"]

def write_case_guide(ev, inbox_data):
    import collections
    from world import CENTRES
    cname = {k: n for k, n, *_ in CENTRES} if CENTRES and len(CENTRES[0]) > 1 else {}
    lines = ["# Case guide (EVALUATOR ONLY)", "",
             "Do not feed this file, `ground_truth.json`, `voice_scripts.json` or `true_stock.csv` to the app. They exist so you can mark what the app did.", "",
             "Twenty cases arrive on Saturday 21 Nov 2026 between 06:45 and 10:00 IST, through four triggers: household message (WhatsApp, app), household call, brand-forwarded request, retailer handover.",
             "Each case names the receiving centre, the raw input, what a careful human would conclude, and what the app is expected to do at each gate. `evaluator_only/personas/<case>.md` tells whoever plays the household how to answer; it holds the real situation, so it never goes to the app.", ""]
    by = collections.Counter(s["trigger"] for s in STORIES)
    lines += ["| Trigger | Cases |", "|---|---|"] + [f"| {t.replace('_', ' ')} | {', '.join(x['id'] for x in STORIES if x['trigger'] == t)} |" for t in by] + [""]
    for s in STORIES:
        cid = s["id"]; g = GROUND_TRUTH[cid]; c = next(x for x in inbox_data if x["case_id"] == cid)
        lines += [f"## {cid}. {s['sender']}", "",
                  f"- Trigger and channel: {s['trigger'].replace('_', ' ')} via {s['channel']}",
                  f"- Receiving centre: {cname.get(s['centre'], s['centre'])} (`{s['centre']}`)",
                  f"- Number: {'known to Keepwell' if c['number_known_to_keepwell'] else 'new to Keepwell'}"]
        if "messages" in c:
            lines.append(f"- Inputs: {', '.join(m['type'] for m in c['messages'])}")
        else:
            lines.append(f"- Inputs: {c['payload'].get('kind')} payload" + (f" with {len(c['payload'].get('attachments', []))} attachment(s)" if c["payload"].get("attachments") else ""))
        if s.get("stage_candidate"): lines.append("- **Best case for the stage prototype**")
        for k, lab in (("fault", "Fault"), ("job_type", "Job type"), ("root_cause", "Root cause"), ("parts", "Parts"), ("min_skill_level", "Min technician level"), ("duration_min", "Duration (min)"),
                       ("urgency_class", "Urgency class"), ("safety", "Safety issue"), ("requires_cert", "Certification"), ("entitlement", "Entitlement"),
                       ("first_time_fix_possible", "First-visit fix possible")):
            if k in g and g[k] not in (None, [], ""):
                lines.append(f"- {lab}: {g[k]}")
        if g.get("expect"):
            lines.append("- Expected behaviour:")
            lines += [f"  - **{k}**: {v}" for k, v in g["expect"].items() if k != "best_stage_case"]
        if g.get("traps"):
            lines.append("- Traps:"); lines += [f"  - {t}" for t in g["traps"]]
        lines.append("")
    with open(os.path.join(ev, "CASE_GUIDE.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

def main(out):
    if os.path.exists(out):
        shutil.rmtree(out)
    os.makedirs(out)
    catalogue.build_catalogue(); catalogue.build_rates()
    world.build_coverage_and_policy()
    truth = world.build_supply()
    world.build_centre_prices()
    people.build_story_households()
    people.build_random_households(150)
    history.simulate_history()
    print('purged future-spilling tickets:', history.purge_future())
    history.story_history()
    history.historic_reminders()
    infl = schedule.build_inflight(26)
    schedule.build_calendars(infl)
    history.build_routes()
    history.build_metrics()
    history.build_experience(520)
    paths = kb.build_all(os.path.join(out, "kb"))
    kb.register_kb_rows(paths)
    pages = kb.find_manual_pages(paths)
    safefix.build_safe_fixes(pages)
    safefix.build_urgency_rules()
    print('adaptation:', adapt.build_adaptation())
    # ---- tables
    for t in APP_OUTPUT_TABLES:
        assert not TABLES.get(t), f"{t} must be empty at seed time, found {len(TABLES[t])}"
    manifest = write_csvs(os.path.join(out, "csv"), ORDER)
    seeded = {m[0] for m in manifest}
    leftovers = [t for t in TABLES if TABLES[t] and t not in ORDER]
    assert not leftovers, leftovers
    # ---- load.sql
    with open(os.path.join(out, "load.sql"), "w") as f:
        f.write("-- Loads the simulated dataset. Run from the dataset root:  psql -d keepwell -v ON_ERROR_STOP=1 -f load.sql\n")
        f.write("-- Schema (keepwell_schema.sql) must already be applied. Append-only triggers are not affected: appliance_event rows are inserted, never updated.\n")
        f.write("BEGIN;\nSET search_path = kw, public;\nSET kw.role = 'platform';\n")
        for t, cols, n in manifest:
            f.write(f"\\copy {t} ({', '.join(cols)}) FROM 'csv/{t}.csv' WITH (FORMAT csv, HEADER true, NULL '\\N')\n")
        f.write("COMMIT;\nANALYZE;\n")
    # ---- media / inbox
    if os.environ.get('SKIP_INBOX'):
        print('SKIP_INBOX set: tables only'); return
    ib, gt_voice, phones = inbox.build_inbox(os.path.join(out, "inbox"))
    # ---- evaluator only
    ev = os.path.join(out, "evaluator_only"); os.makedirs(ev, exist_ok=True)
    with open(os.path.join(ev, "true_stock.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(truth[0].keys())); w.writeheader(); w.writerows(truth)
    gt = {}
    for cid, g in GROUND_TRUTH.items():
        gt[cid] = {**g, "sender_phone": phones.get(cid)}
    with open(os.path.join(ev, "ground_truth.json"), "w", encoding="utf-8") as f:
        json.dump(gt, f, ensure_ascii=False, indent=2, default=str)
    with open(os.path.join(ev, "voice_scripts.json"), "w", encoding="utf-8") as f:
        json.dump(gt_voice, f, ensure_ascii=False, indent=2)
    write_case_guide(ev, ib)
    with open(os.path.join(out, "manifest.json"), "w") as f:
        json.dump([{"table": t, "rows": n, "columns": c} for t, c, n in manifest], f, indent=1)
    print("tables", len(manifest), "rows", sum(n for _, _, n in manifest))
    for t, c, n in manifest:
        print(f"  {t:28s}{n:6d}")

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "/home/claude/keepwell_sim/out")
