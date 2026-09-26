"""Rules-engine eval on ground-truth evidence (T3.2, R6). Free: no API calls.

Usage: python scripts/run_rules_eval.py            # dev split
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from evals.harness import rules_eval as R  # noqa: E402

if __name__ == "__main__":
    summary, _ = R.run_truth("dev")
    md = R.write(summary, "dev_truth")
    print(md.read_text(encoding="utf-8"))
