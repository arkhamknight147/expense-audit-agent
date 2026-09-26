"""Anomaly-check eval (T3.3). Dev split only.

Usage:
  python scripts/run_anomaly_eval.py            # ground truth, free
  python scripts/run_anomaly_eval.py --real     # real extraction on dev anomaly + red-team claims (~Rs 50; cached receipts are free)
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from evals.harness import anomaly_eval as A  # noqa: E402

if __name__ == "__main__":
    if "--real" in sys.argv:
        import anthropic
        from expense_audit import extract as X
        client = anthropic.Anthropic(max_retries=5)
        cached = lambda img: (X.CACHE_DIR / f"{X._cache_key((ROOT / img).read_bytes(), X.EXTRACT_MODEL)}.json").exists()  # noqa: E731
        summary, tag = A.run_real(lambda img: X.extract_receipt(img, client=client), cached), "dev_real"
    else:
        summary, tag = A.run_truth(), "dev_truth"
    print(A.write(summary, tag).read_text(encoding="utf-8"))
