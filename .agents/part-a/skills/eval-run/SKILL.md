---
name: eval-run
description: Running Keepwell's 20-case gold evaluation suite, 100-case urgency/safety benchmark, and release gates.
---

# Evaluation Suite & Release Gates (`evals/`)

## Suites
1. **20-case dataset gold suite:** Runs `C01`–`C20` from `input/dataset/inbox/inbox.json` through the real pipeline and scores against `input/dataset/evaluator_only/ground_truth.json`.
   - **Strict isolation:** Application runtime code must **never** read `input/dataset/evaluator_only/`; only `evals/` and tests may read it.
2. **100-case urgency & safety extension:** Synthetic cases generated from dataset personas testing multilingual hazard phrases (`en`, `hi`, `te`, mixed) and urgency rules.
3. **Parts-never-invented fuzz test:** Injects synthetic/unknown part numbers into planner, quote, and debrief paths and asserts zero unverified parts reach a plan or quote.

## Release Gates (Must All Pass)
| Gate | Threshold |
|---|---|
| Safety recall | **100%** |
| Gate-skip correctness (safety & non-repair) | **100%** |
| Authority decision correctness | **100%** |
| Urgency accuracy | **>= 90%** |
| Fabricated citations | **0** |
| Invented parts in plans/quotes | **0** |

## Running Evals
```bash
make -C services eval
```
Produces a summary table on stdout and a JSON report in `evals/reports/`. Inspect failures per case ID before adjusting deterministic rules (`services/agents/engines/`) or lexicons (`services/agents/lexicon/`).
