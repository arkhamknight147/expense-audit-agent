"""Render policy/POLICY.md from policy/limits.yaml (single source of truth, ADR-009).

Also validates that every clause ID in the registry appears exactly once in the
rendered policy, and that no unregistered clause ID appears. Exits non-zero on mismatch.

Usage: python scripts/build_policy.py
"""
from pathlib import Path
import re
import sys

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined

ROOT = Path(__file__).resolve().parents[1]
POLICY_DIR = ROOT / "policy"


def main() -> int:
    cfg = yaml.safe_load((POLICY_DIR / "limits.yaml").read_text(encoding="utf-8"))
    titles = {c["id"]: c["title"] for c in cfg["clauses"]}

    env = Environment(
        loader=FileSystemLoader(POLICY_DIR / "templates"),
        undefined=StrictUndefined,
        keep_trailing_newline=True,
    )
    out = env.get_template("POLICY.md.j2").render(**cfg, t=titles)

    found = re.findall(r"^### ([A-Z]+-\d{2}) — ", out, flags=re.M)
    errors = []
    for cid in titles:
        n = found.count(cid)
        if n != 1:
            errors.append(f"{cid}: appears {n} times in rendered policy (expected 1)")
    for cid in set(found) - set(titles):
        errors.append(f"{cid}: in template but not in clause registry")
    overlap = set(cfg["city_tiers"]["X"]) & set(cfg["city_tiers"]["Y"])
    if overlap:
        errors.append(f"cities in both X and Y: {sorted(overlap)}")
    if errors:
        print("Policy build FAILED:\n  " + "\n  ".join(errors))
        return 1

    (POLICY_DIR / "POLICY.md").write_text(out, encoding="utf-8")
    print(f"Wrote policy/POLICY.md ({len(found)} clauses)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
