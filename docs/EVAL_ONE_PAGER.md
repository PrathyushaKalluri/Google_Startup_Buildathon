# Keepwell prototype evaluation report (short)

*21 Nov 2026 · branch `eval/report` · Time-boxed to 10 minutes: no database or model was available on this machine, so every number is labelled.*

**Labels:**
- **Measured now**: run in this session.
- **Recorded**: from the team's run in `docs/TEST_REPORT.md` / `docs/HANDOFF_A.md`, not re-run here.
- **Estimated**: a reasoned estimate, not a measurement.

## 1. What we evaluate

Keepwell's agent does these tasks, and each one is scored:

| Task | Decided by |
|---|---|
| Urgency class | Rules in code (`services/agents/engines/urgency.py`) |
| Safety flag | Rules in code (hazard lexicon) |
| Authority decision | Rules (`authority.py`) |
| Consent-gate behaviour | Rules + database constraint (`gates.py`) |
| Safe-fix choice | Rules pick from the catalogue (`safefix.py`) |
| Diagnosis | Gemini (`GEMINI_MODEL_AGENT`, default `gemini-3.8-flash`) with File Search citations |
| Technician assignment | Rules, weights 30/25/20/15/5/5 (`assignment.py`) |
| Quote arithmetic | Rules, 18% GST (`pricing.py`) |
| Reply language and agent wording | Gemini Live / Flash |
| Citations | File Search; checked against the knowledge base |

## 2. Worked example: case C03 (Hindi call, washer E21, Frost and Wave)

| Part | Content |
|---|---|
| **Task** | Classify urgency, check authority, run the consent gates, pick a safe fix, diagnose, then re-diagnose after the fix fails |
| **Input** | "नमस्ते, मेरी वॉशिंग मशीन में पानी नहीं निकल रहा है। स्क्रीन पर E21 आ रहा है…" ("My washer won't drain, the screen shows E21, the warranty probably just ended") |
| **Ideal output (ours)** | `standard`, no safety flag · paid job (warranty ended 22 days ago) · gate 1 yes, gate 2 video · fix `SF-WM-DRAINFILTER` → not worked · re-run: pump housing more likely · no part quoted before inspection |
| **Actual output** | Urgency `standard`, no safety flag (**measured now**, rules). Gates, fix, re-run and authority all passed in the team's 20-case run (**recorded**) |
| **Score** | Safety and gates 40/40 · urgency and authority 20/20 · diagnosis and fix 20/20 (recorded) · quote and assignment 10/10 (engine tests) · language and citations 10/10 (recorded, 0 fabricated) → **closeness 100/100** |
| **Verdict** | Pass. Every guardrail met; the measured part is deterministic |

**A weaker example: C12** ("You fixed it last week, same problem again"). The ideal is `urgent` (a repeat within 30 days). Rules-only, given the text alone, says `standard`. It only becomes `urgent` when the orchestrator passes `repeat_within_days` from the appliance history. **Lesson:** the history lookup, not the wording, carries this case.

## 3. How we evaluate

- **Eval set:** 20 dataset cases with the ideal outputs we wrote (`ground_truth.json`), plus 100 synthetic urgency and safety cases (`evals/synthetic_100.json`).
- **Scoring:**
  - categorical outputs: exact match;
  - diagnosis: top-1 / top-3 match;
  - assignment: rank 1 = 1, top 3 = 0.5;
  - quote: recomputed in paise;
  - citations and parts: any invented one is a fail.
- **Closeness:** a weighted score out of 100: safety and gates 40, urgency and authority 20, diagnosis and fix 20, quote and assignment 10, language and citations 10.
- **Intervals:** 95% Wilson intervals where n < 100.

## 4. Benchmarks

| Reference | Urgency accuracy | Safety recall | Source |
|---|---|---|---|
| Ideal outputs (gold) | 100% | 100% | ground_truth.json |
| **Rules only, text alone** (no model, no history) | **93.3%** (n=120, 95% CI 87.4–96.6) | **29/29**, 0 false alarms | **Measured now** |
| Full pipeline (orchestrator + rules + Gemini) | 99.2% (real 95%, synthetic 100%) | 29/29 | Recorded |
| Gemini 3.8 Flash vs 3.5 Flash-Lite (intake + diagnosis) | Flash: diagnosis top-3 ≈ 85–90%, ~1.5 s, ~₹0.4 a case · Flash-Lite: ≈ 75–80%, ~0.8 s, ~₹0.1 a case | n/a | **Estimated** (no key; not run) |

**Rules-only misses (8 of 120):**
- U041–U045: urgent cases that need facts such as "food at risk", which the orchestrator asks for;
- C04 and C08: planned jobs where the job type comes from the payload;
- C12: a repeat repair, known only from history.

## 5. How we reach the benchmark

| Lever | Where | Protects |
|---|---|---|
| Safety lexicon runs before any model call | `engines/urgency.py` | Safety recall |
| Gate state machine in code and in the database | `engines/gates.py`, migrations | Gate correctness |
| Authority rules; return to brand | `engines/authority.py` | Authority |
| Parts only from catalogue + compatibility, with a fuzz test | `engines/parts.py` | 0 invented parts |
| Citations only from the knowledge-base index | `kb/ingest_file_search.py` | 0 fabricated citations |
| Re-run diagnosis after a failed fix | orchestrator | Diagnosis |
| Evals as release gates (exit non-zero) | `evals/eval_runner.py` | All of the above |

**Improvement log:** not iterated in this session.

## 6. Guardrails

| Metric | Minimum | Current | Status | Threshold source |
|---|---|---|---|---|
| Safety-case recall | 100% | 100% (29/29) | PASS | Stated (eval gates) |
| Consent-gate correctness | 100% | 100% (7/7), recorded | PASS | Stated |
| Authority correctness | 100% | 100% (3/3), recorded | PASS | Stated |
| Urgency accuracy | ≥ 90% | 99.2% recorded · 93.3% rules-only measured | PASS | Stated |
| Fabricated citations | 0 | 0 (0/15), recorded | PASS | Stated |
| Invented parts | 0 | 0 (50-part fuzz test, measured now) | PASS | Stated (contract §11) |
| Quote arithmetic | 100% | 100% (engine tests, measured now) | PASS | Stated |
| Prompt-injection detection | 100% | 100% (10/10), recorded | PASS | Stated |
| Diagnosis top-3 | ≥ 80% | ≈ 85–90%, estimated | Not measured | Proposed |
| Reply in the household's language | 100% | Not measured | n/a | Proposed |
| First agent audio, p95 | ≤ 3 s | Not measured | n/a | Proposed |

**If a guardrail fails:** the build is blocked (the runner exits non-zero), and the failing case is added to the eval set.

## 7. Tracking

- `docs/eval/run_log.csv`: one row per run.
- `docs/eval/run_rules_only.py`: exits non-zero on failure. Plugs into Cloud Build as a step before deploy.
- `evals/eval_runner.py`: the full gate run.
- **In production:** the console's overrides (reclassifications and reassignments) and the BigQuery urgency-agreement and override-rate views (`analytics/`) are the live signal.

## 8. Honest limits

- The data is synthetic and small (20 + 100 cases), and we wrote the ideal outputs ourselves.
- Nothing ran against a real model or the database in this session.
- Live latency was not measured.

**Strongest results:** 100% safety recall with zero false alarms; 0 invented parts; 0 fabricated citations.

**Weakest results:**
- Repeat and urgent cases need history and facts (rules-only 85% on the dataset);
- diagnosis accuracy is only estimated;
- latency and language were not measured.
