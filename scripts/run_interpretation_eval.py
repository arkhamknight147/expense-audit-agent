"""Interpretation eval (T3.4) on the dev judgement slice. Dev only.

Usage:
  python scripts/run_interpretation_eval.py --dry-run   # fake model, no cost: checks the plumbing
  python scripts/run_interpretation_eval.py             # Sonnet x3 per grey line (~Rs 40-60)
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from evals.harness import interpretation_eval as I  # noqa: E402

if __name__ == "__main__":
    if "--dry-run" in sys.argv:
        summary, rows = I.run(client=I.OracleClient(), use_cache=False)
        tag = "dev_dryrun"
    else:
        import anthropic
        summary, rows = I.run(client=anthropic.Anthropic(max_retries=5))
        tag = "dev"
    print(I.write(summary, rows, tag).read_text(encoding="utf-8"))
