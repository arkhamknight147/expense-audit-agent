"""Run the extraction eval (T3.1) on the DEV split. Never run on the locked test set here.

Usage:
  python scripts/run_extraction_eval.py --dry-run        # no API calls: checks the harness (should score 100%)
  python scripts/run_extraction_eval.py --limit 20       # smoke run: 20 receipts spread across types (~Rs 7)
  python scripts/run_extraction_eval.py                  # full dev set (~710 receipts, ~Rs 230-260)
Options: --concurrency 4 (lower it if you hit rate limits), --no-cache
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from evals.harness import extraction as H  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-cache", action="store_true")
    ap.add_argument("--rescore", metavar="TAG", help="re-score the latest raw results for TAG (no API calls), e.g. dev_sample200_sonnet-5")
    a = ap.parse_args()
    if a.rescore:
        md = H.rescore_latest(a.rescore)
        print(md.read_text(encoding="utf-8"))
        return 0

    items = H.load_items("dev")
    if a.limit:
        items = H.sample(items, a.limit)
    from expense_audit.config import EXTRACT_MODEL
    model_tag = EXTRACT_MODEL.replace("claude-", "").split("-2025")[0]
    tag = "dryrun" if a.dry_run else ((f"dev_smoke{a.limit}" if a.limit <= 20 else f"dev_sample{a.limit}") + f"_{model_tag}" if a.limit else f"dev_{model_tag}")
    print(f"Extraction eval: {len(items)} dev receipts ({tag})")

    if a.dry_run:
        fn = H.oracle_extract(items)
        usd_inr = 88.0
    else:
        from expense_audit.config import USD_INR
        from expense_audit.extract import extract_receipt
        import anthropic
        client = anthropic.Anthropic(max_retries=5)
        fn = lambda img: extract_receipt(img, client=client, use_cache=not a.no_cache)  # noqa: E731
        usd_inr = USD_INR

    rows = H.run(items, fn, concurrency=a.concurrency)
    summary = H.summarise(rows, usd_inr=usd_inr)
    raw, md = H.write_outputs(rows, summary, tag)
    print(md.read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
