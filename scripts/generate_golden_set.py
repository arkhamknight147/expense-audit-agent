"""Generate the synthetic golden set (EVAL_PLAN §2). Deterministic (fixed seed).

Usage:
  python scripts/generate_golden_set.py            # data + receipt images
  python scripts/generate_golden_set.py --no-render  # data only (fast)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evals.generator.build import main  # noqa: E402

if __name__ == "__main__":
    main(render="--no-render" not in sys.argv)
