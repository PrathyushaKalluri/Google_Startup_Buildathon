"""DB-free rules-only eval: urgency + safety on 100 synthetic and 20 dataset cases (deterministic engine, no model)."""
import json, sys, csv, math, subprocess, datetime
from pathlib import Path
R = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(R))
from services.agents.engines.urgency import assess_urgency
def wilson(k, n, z=1.96):
    if n == 0: return (0, 0)
    p = k / n; d = 1 + z*z/n; c = p + z*z/(2*n); h = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))
    return round((c-h)/d*100, 1), round((c+h)/d*100, 1)
syn = json.load(open(R/'evals/synthetic_100.json'))
gt = json.load(open(R/'input/dataset/evaluator_only/ground_truth.json'))
inbox = json.load(open(R/'input/dataset/inbox/inbox.json'))
vs = json.load(open(R/'input/dataset/evaluator_only/voice_scripts.json'))
rows = []
for c in syn:
    r = assess_urgency(text=c['text'], category_code=c.get('category_code'), job_type=c.get('job_type', 'repair'))
    rows.append(dict(set='synthetic', id=c['id'], expected=c['expected_urgency'], got=r.urgency_class, exp_safety=c['expected_safety_flag'], got_safety=r.safety_flag))
for case in sorted(inbox, key=lambda c: c['case_id']):
    cid = case['case_id']; parts = []
    for m in case.get('messages') or []:
        t = m.get('type')
        if t == 'text': parts.append((m.get('text') or {}).get('body') or '')
        elif t == 'audio': parts.append((vs.get((m.get('audio') or {}).get('file') or '') or {}).get('transcript_original_script', ''))
        elif t == 'call': parts.append((vs.get(((m.get('call') or {}).get('recording') or {}).get('file') or '') or {}).get('transcript_original_script', ''))
        elif t == 'image': parts.append((m.get('image') or {}).get('caption') or '')
    p = case.get('payload') or {}
    for k in ('complaint', 'notes', 'brand_note'):
        if p.get(k): parts.append(str(p[k]))
    job = 'installation' if (p.get('requested_job') == 'installation' or case['trigger'] == 'retailer_handover') else 'repair'
    r = assess_urgency(text=' '.join(parts), job_type=job)
    rows.append(dict(set='dataset', id=cid, expected=gt[cid]['urgency_class'], got=r.urgency_class, exp_safety=bool(gt[cid]['safety']), got_safety=r.safety_flag))
out = {}
for s in ('synthetic', 'dataset', 'all'):
    rr = [x for x in rows if s == 'all' or x['set'] == s]
    k = sum(x['expected'] == x['got'] for x in rr); n = len(rr)
    sk = [x for x in rr if x['exp_safety']]; sp = sum(x['got_safety'] for x in sk)
    fp = sum(1 for x in rr if not x['exp_safety'] and x['got_safety'])
    out[s] = dict(n=n, urgency_acc=round(100*k/n, 1), urgency_ci=wilson(k, n), safety_recall=f"{sp}/{len(sk)}", safety_ci=wilson(sp, len(sk)), safety_false_alarms=fp)
misses = [x for x in rows if x['expected'] != x['got']]
with open(R/'docs/eval/results.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
commit = subprocess.run(['git', '-C', str(R), 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True).stdout.strip()
log = R/'docs/eval/run_log.csv'; new = not log.exists()
with open(log, 'a', newline='') as f:
    w = csv.writer(f)
    if new: w.writerow(['date', 'commit', 'mode', 'n', 'urgency_acc_all', 'safety_recall_all', 'safety_false_alarms', 'gate_urgency_ge_90', 'gate_safety_100'])
    a = out['all']; sr = a['safety_recall'].split('/')
    w.writerow([datetime.datetime.now().isoformat(timespec='minutes'), commit, 'rules-only (no model, no DB)', a['n'], a['urgency_acc'], a['safety_recall'], a['safety_false_alarms'], 'PASS' if a['urgency_acc'] >= 90 else 'FAIL', 'PASS' if sr[0] == sr[1] else 'FAIL'])
print(json.dumps(out, indent=1)); print('misses:', [(m['id'], m['expected'], m['got']) for m in misses])
json.dump(dict(summary=out, misses=misses), open(R/'docs/eval/last_rules_only.json', 'w'), indent=1)
a = out['all']; sr = a['safety_recall'].split('/')
sys.exit(0 if (a['urgency_acc'] >= 90 and sr[0] == sr[1]) else 1)
