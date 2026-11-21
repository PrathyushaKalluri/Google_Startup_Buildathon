"""Builds DATA_DICTIONARY.md from keepwell_schema.sql: every table with its purpose, columns, types, keys, allowed values and notes; then views and functions."""
import re, sys

def parse(path):
    lines = open(path, encoding="utf-8").read().splitlines()
    out, section, pending = [], None, []
    i = 0
    while i < len(lines):
        ln = lines[i]
        m = re.match(r"-- (\d+)\. (.*)", ln)
        if m:
            section = f"{m.group(1)}. {m.group(2)}"; pending = []
        elif ln.startswith("--") and not ln.startswith("-- ---") and not ln.startswith("-- ==="):
            pending.append(ln[2:].strip())
        elif ln.startswith("CREATE TABLE") or ln.startswith("CREATE VIEW") or ln.startswith("CREATE FUNCTION"):
            kind = ln.split()[1]
            name = re.match(r"CREATE (?:TABLE|VIEW|FUNCTION) (\w+)", ln).group(1)
            body = []
            if kind == "TABLE":
                i += 1
                while not lines[i].startswith(");"):
                    cur = lines[i]
                    while cur.split("--")[0].count("(") > cur.split("--")[0].count(")"):
                        i += 1; cur += " " + lines[i].strip()
                    body.append(cur); i += 1
            out.append(dict(kind=kind, name=name, section=section, doc=" ".join(pending), body=body, head=ln))
            pending = []
        elif ln.strip() and not ln.startswith("--"):
            pending = []
        i += 1
    return out

def column(ln):
    ln = ln.rstrip().rstrip(",")
    note = ""
    if "--" in ln:
        ln, note = ln.split("--", 1); note = note.strip(); note = re.sub(r"\s*@(geo|vec)\b", "", note)
    ln = ln.strip()
    if not ln or re.match(r"(PRIMARY|UNIQUE|CHECK|FOREIGN|EXCLUDE|CONSTRAINT)\b", ln):
        return None
    m = re.match(r"(\w+)\s+((?:[a-z]+(?:\([^)]*\))?(?:\[\])?)(?:\s+(?:with|without)\s+time\s+zone)?)(.*)", ln)
    if not m:
        return None
    name, typ, rest = m.groups()
    attrs = []
    if "PRIMARY KEY" in rest: attrs.append("PK")
    if "NOT NULL" in rest: attrs.append("required")
    if re.search(r"\bUNIQUE\b", rest): attrs.append("unique")
    fk = re.search(r"REFERENCES (\w+)\((\w+)\)", rest)
    if fk: attrs.append(f"→ {fk.group(1)}")
    vals = re.search(r"IN \(([^)]*)\)", rest)
    if vals:
        v = [x.strip().strip("'") for x in re.split(r",\s*", re.sub(r"\s+", " ", vals.group(1)))]
        attrs.append("values: " + " / ".join(v))
    d = re.search(r"DEFAULT ('[^']*'|[^\s,]+)", rest)
    if d and "gen_random_uuid" not in d.group(1) and "current_centre" not in d.group(1) and not d.group(1).startswith("now"):
        attrs.append("default " + d.group(1))
    if "current_centre()" in rest: attrs.append("set from session centre")
    return name, typ.strip(), "; ".join(attrs), note

def table_checks(body):
    out = []
    for ln in body:
        s = ln.strip().rstrip(",")
        if s.startswith("CHECK") or s.startswith("UNIQUE") or s.startswith("EXCLUDE"):
            out.append(re.sub(r"\s+", " ", s.split("--")[0].strip()))
    return out

def build(schema_path, out_path):
    items = parse(schema_path)
    L = ["# Data dictionary (schema v0.2)", "",
         "Generated from `keepwell_schema.sql`. Money is in paise. Times are timestamptz (IST in the CSVs). Geography columns are loaded from EWKT (`SRID=4326;POINT(lon lat)`). "
         "Tables marked **centre-owned** carry `centre_id` and are isolated by row-level security. Tables marked **app output** are empty in the seed because the app writes them.", ""]
    RLS = "ticket conversation urgency_assessment consent_gate clarifying_qa diagnosis_session diagnosis_media fix_attempt visit_plan plan_hypothesis plan_part assignment_candidate slot_proposal quote quote_line visit visit_media visit_part_used reservation route route_stop settlement_line feedback reminder brand_referral retailer_handover centre_price technician technician_skill technician_availability technician_metrics centre_commercial".split()
    OUT = "visit_plan plan_hypothesis plan_part assignment_candidate slot_proposal visit_media access_log identity_merge".split()
    cur = None
    tables = [x for x in items if x["kind"] == "TABLE"]
    for sec in dict.fromkeys(x["section"] for x in tables):
        L += [f"## {sec}", ""]
        for t in [x for x in tables if x["section"] == sec]:
            tags = []
            if t["name"] in RLS: tags.append("centre-owned")
            if t["name"] in OUT: tags.append("app output")
            L += [f"### {t['name']}" + (f"  ({', '.join(tags)})" if tags else ""), ""]
            if t["doc"]: L += [t["doc"], ""]
            L += ["| Column | Type | Constraints and values | Note |", "|---|---|---|---|"]
            for b in t["body"]:
                c = column(b)
                if c: L.append("| " + " | ".join(x.replace("|", "/") for x in c[:1]) + f" | {c[1]} | {c[2]} | {c[3]} |")
            ch = table_checks(t["body"])
            if ch:
                L += ["", "Table rules:"] + [f"- `{x}`" for x in ch]
            L.append("")
    views = [x for x in items if x["kind"] == "VIEW"]
    if views:
        L += ["## Views", ""]
        for v in views:
            L += [f"- **{v['name']}**" + (f": {v['doc']}" if v["doc"] else "")]
        L.append("")
    fns = [x for x in items if x["kind"] == "FUNCTION"]
    L += ["## Functions", ""]
    for f in fns:
        L += [f"- `{re.sub(r'^CREATE FUNCTION ', '', f['head']).strip()}`" + (f" {f['doc']}" if f["doc"] else "")]
    open(out_path, "w", encoding="utf-8").write("\n".join(L) + "\n")
    return len(tables), len(views), len(fns)

if __name__ == "__main__":
    print(build(sys.argv[1], sys.argv[2]))
