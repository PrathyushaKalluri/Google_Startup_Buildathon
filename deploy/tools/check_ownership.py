#!/usr/bin/env python3
"""Ownership check (contract section 2): list files a part branch changed outside its owned folders."""
from __future__ import annotations

import subprocess
import sys

A = ["db/", "services/", "kb/", "analytics/", "evals/", "infra/backend/", ".agents/part-a/",
     "docs/NOTES_A.md", "docs/DECISIONS_A.md", "docs/HANDOFF_A.md", "docs/rubric_A.md", "docs/TESTING_A.md"]
B = ["apps/", "mocks/", "infra/frontend/", "docs/design/", ".agents/part-b/",
     "docs/NOTES_B.md", "docs/DECISIONS_B.md", "docs/HANDOFF_B.md", "docs/rubric_B.md", "docs/evidence/"]
SHARED = ["contract/", ".gitignore", ".agents/rules/", "AGENTS.md", "GEMINI.md"]
BRANCHES = {"origin/part-a/agent-core": A, "origin/part-b/experience": B}


def changed(branch: str, base: str) -> list[str]:
    out = subprocess.run(["git", "diff", "--name-only", f"{base}...{branch}"], capture_output=True, text=True, check=True)
    return [x for x in out.stdout.splitlines() if x]


def main() -> int:
    base = sys.argv[1] if len(sys.argv) > 1 else "origin/main"
    bad = 0
    for br, owned in BRANCHES.items():
        for f in changed(br, base):
            if not any(f.startswith(p) or f == p for p in owned + SHARED):
                print(f"VIOLATION {br}: {f}")
                bad += 1
    print(f"ownership violations: {bad}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
