"""Format-only validation of PM judgement labels (evals/labelling/judgement_cases.csv).

Checks structure and the mechanical decision rules from LABELLING_GUIDE.md.
It does NOT judge whether a verdict is right. Exits non-zero on any error.
"""
import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "evals" / "labelling" / "judgement_cases.csv"
LABELS = ROOT / "evals" / "golden" / "labels.jsonl"
POLICY = ROOT / "policy" / "POLICY.md"

VERDICTS = {"compliant", "non_compliant", "unclear"}
DECISIONS = {"auto_approve", "escalate", "return_to_employee"}
COLUMNS = ["claim_id", "candidate_clause", "scenario_summary", "claim_total", "over_cap", "receipts",
           "clause_verdict", "expected_decision", "violated_clause_ids", "reasoning", "relabel_clause_verdict"]


def main() -> int:
    rows = list(csv.DictReader(open(CSV, encoding="utf-8-sig", newline="")))
    errors = []
    if not rows or list(rows[0].keys()) != COLUMNS:
        errors.append(f"columns differ from expected: {list(rows[0].keys()) if rows else 'no rows'}")
    expected_ids = {json.loads(l)["claim_id"] for l in open(LABELS, encoding="utf-8")
                    if json.loads(l)["slice"] == "judgement"}
    ids = [r["claim_id"] for r in rows]
    if set(ids) != expected_ids or len(ids) != len(set(ids)):
        errors.append(f"claim_id set mismatch (got {len(ids)} rows, expected {len(expected_ids)} unique judgement IDs)")
    clause_ids = set(re.findall(r"^### ([A-Z]+-\d{2}) — ", POLICY.read_text(encoding="utf-8"), flags=re.M))
    for r in rows:
        cid, v, d = r["claim_id"], r["clause_verdict"].strip(), r["expected_decision"].strip()
        over = r["over_cap"].strip().upper() == "TRUE"
        viol = [x.strip() for x in r["violated_clause_ids"].split(";") if x.strip()]
        if v not in VERDICTS:
            errors.append(f"{cid}: clause_verdict '{v}' not allowed")
        if d not in DECISIONS:
            errors.append(f"{cid}: expected_decision '{d}' not allowed")
        want = "escalate" if (over or v in ("non_compliant", "unclear")) else "auto_approve"
        if d and v in VERDICTS and d != want:
            errors.append(f"{cid}: decision '{d}' breaks the mechanical rule (expected '{want}')")
        if v == "non_compliant" and not viol:
            errors.append(f"{cid}: non_compliant but violated_clause_ids is empty")
        if v != "non_compliant" and viol:
            errors.append(f"{cid}: violated_clause_ids set but verdict is '{v}'")
        for x in viol:
            if x not in clause_ids:
                errors.append(f"{cid}: unknown clause id '{x}'")
        if not r["reasoning"].strip():
            errors.append(f"{cid}: reasoning is empty")
    if errors:
        print("Judgement labels INVALID:\n  " + "\n  ".join(errors))
        return 1
    print(f"Judgement labels OK: {len(rows)} rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
