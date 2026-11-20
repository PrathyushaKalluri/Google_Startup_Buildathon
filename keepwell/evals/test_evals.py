"""Pytest suite for Keepwell Part A Evaluation Harness (Work-Stream A6-Evals)."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from evals.eval_runner import LAST_REPORT_PATH, SYNTHETIC_PATH, run_all_evals


def test_synthetic_100_distribution() -> None:
    cases = json.loads(SYNTHETIC_PATH.read_text(encoding="utf-8"))
    assert len(cases) == 100

    buckets = Counter(c["bucket"] for c in cases)
    assert buckets["safety"] >= 25
    assert buckets["urgent"] >= 25
    assert buckets["standard"] >= 25
    assert buckets["planned"] >= 15
    assert buckets["adversarial"] >= 10

    safety_langs = {c["language"] for c in cases if c["bucket"] == "safety"}
    assert safety_langs == {"en", "hi", "te"}

    categories = {c["category_code"] for c in cases}
    assert categories == {"ac", "refrigerator", "washing_machine", "ro_purifier", "geyser"}


def test_all_release_gates_pass() -> None:
    report = run_all_evals(write_report=True)
    assert LAST_REPORT_PATH.exists()
    assert report["real_cases_evaluated"] == 20
    assert report["synthetic_cases_evaluated"] == 100

    gates = report["gates"]
    assert gates["safety_recall"]["passed"] is True, gates["safety_recall"]
    assert gates["gate_skip_correctness"]["passed"] is True, gates["gate_skip_correctness"]
    assert gates["authority_correctness"]["passed"] is True, gates["authority_correctness"]
    assert gates["urgency_accuracy"]["passed"] is True, gates["urgency_accuracy"]
    assert gates["zero_fabricated_citations"]["passed"] is True, gates["zero_fabricated_citations"]
    assert report["model_armor_adversarial"]["rate_pct"] == 100.0
    assert report["all_gates_passed"] is True
