"""Interpretation eval (T3.4, I5) on the dev judgement slice.

Uses ground-truth evidence (like R6) so interpretation quality is measured separately from
extraction. Compares the model's clause verdict with the PM label and simulates the I4(b)
decision: auto-approve only if every interpretation is a unanimous, validly cited
`compliant`, nothing else is flagged, and the claim is under the cap.
"""
from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from expense_audit import policy
from expense_audit.anomaly import detect
from expense_audit.config import AUTO_APPROVE_CAP, USD_INR
from expense_audit.interpret import InterpretationWire, interpret_claim
from expense_audit.rules import CANNOT, FAIL, GAP, evaluate

from .rules_eval import RESULTS, ROOT, evidence_from_truth, load

LABELS_CSV = ROOT / "evals" / "labelling" / "judgement_cases.csv"


def simulate_decision(claim_total: float, rule_results, anomalies, interpretations) -> str:
    if any(r.status in (FAIL, CANNOT) for r in rule_results) or anomalies or claim_total > AUTO_APPROVE_CAP:
        return "escalate"
    if any(r.status == GAP for r in rule_results):
        return "return_to_employee"
    if all(i["verdict"] == "compliant" and i["unanimous"] and i["citations_valid"] for i in interpretations):
        return "auto_approve"
    return "escalate"


def run(client: Any = None, use_cache: bool = True) -> tuple[dict, list[dict]]:
    claims, labels, ledger = load("dev")
    pm = {r["claim_id"]: r for r in csv.DictReader(open(LABELS_CSV, encoding="utf-8-sig", newline=""))}
    rows = []
    judgement = [c for c in claims if labels[c["claim_id"]]["slice"] == "judgement"]
    print(f"Interpretation eval: {len(judgement)} dev judgement claims")
    for c in judgement:
        lab = labels[c["claim_id"]]
        evs = [evidence_from_truth(li, lab["lines"][li["line_id"]]["truth"], c["trip"]["destination"]) for li in c["line_items"]]
        rr = evaluate(c, evs, ledger)
        an = detect(c, evs, rr)
        interp = interpret_claim(c, evs, rr, client=client, use_cache=use_cache)
        total = sum(li["amount_claimed"] for li in c["line_items"])
        rows.append({"claim_id": c["claim_id"], "clause": lab["grey_clause"], "pm": pm[c["claim_id"]],
                     "interpretations": interp, "decision": simulate_decision(total, rr, an, interp),
                     "rule_fail": [r.clause_id for r in rr if r.status == FAIL]})
    return score(rows), rows


def score(rows: list[dict]) -> dict:
    conf = Counter()
    agree = n = 0
    dec_ok = 0
    false_auto, danger = [], []
    cost = 0.0
    lines = unanimous = cites_ok = unclear = 0
    for r in rows:
        pm_v = r["pm"]["clause_verdict"]
        mine = [i for i in r["interpretations"] if i["clause_id"] == r["clause"]]
        model_v = mine[0]["verdict"] if mine else ("resolved_by_code" if not r["rule_fail"] else "non_compliant")
        conf[(pm_v, model_v)] += 1
        n += 1
        agree += (model_v == pm_v) or (model_v == "resolved_by_code" and pm_v == "compliant")
        if model_v == "compliant" and pm_v != "compliant":
            danger.append((r["claim_id"], r["clause"], pm_v))
        dec_ok += r["decision"] == r["pm"]["expected_decision"]
        if r["decision"] == "auto_approve" and r["pm"]["expected_decision"] != "auto_approve":
            false_auto.append(r["claim_id"])
        for i in r["interpretations"]:
            lines += 1
            unanimous += i["unanimous"]
            cites_ok += i["citations_valid"]
            unclear += i["verdict"] == "unclear"
            cost += i.get("cost_usd") or 0
    return {
        "claims": n, "verdict_agreement": f"{agree}/{n}", "decision_agreement": f"{dec_ok}/{n}",
        "false_auto_approvals": false_auto, "model_compliant_where_pm_not": danger,
        "interpreted_lines": lines, "unanimous": f"{unanimous}/{lines}", "citations_valid": f"{cites_ok}/{lines}",
        "unclear": f"{unclear}/{lines}", "cost_inr_total": round(cost * USD_INR, 2),
        "cost_inr_per_line": round(cost * USD_INR / lines, 2) if lines else 0,
        "confusion": {f"PM {a} / model {b}": v for (a, b), v in sorted(conf.items())},
    }


def write(summary: dict, rows: list[dict], tag: str) -> Path:
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / f"interpretation_{tag}.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    s = summary
    lines = [f"# Interpretation eval — {tag}", "", "Evidence: ground truth. Model verdicts vs PM labels (dev judgement slice).", "",
             "| Metric | Result | Target |", "|---|---|---|",
             f"| Clause verdict agrees with PM | {s['verdict_agreement']} | — |",
             f"| Final decision agrees with PM (I4b) | {s['decision_agreement']} | — |",
             f"| **False auto-approvals** (PM said not auto-approve) | {len(s['false_auto_approvals'])} {s['false_auto_approvals'] or ''} | 0 |",
             f"| Model 'compliant' where PM said otherwise | {len(s['model_compliant_where_pm_not'])} {s['model_compliant_where_pm_not'] or ''} | — |",
             f"| Citations valid (all samples) | {s['citations_valid']} | 100% |",
             f"| Unanimous across 3 samples | {s['unanimous']} | — |",
             f"| Verdict 'unclear' | {s['unclear']} | — |",
             f"| Cost | ₹{s['cost_inr_total']} total, ₹{s['cost_inr_per_line']} per line | — |",
             "", "| PM label / model verdict | Count |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in s["confusion"].items()]
    md = RESULTS / f"interpretation_summary_{tag}.md"
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return md


class OracleClient:
    """Dry-run client: always 'compliant' with a valid citation. Tests plumbing, costs nothing."""
    def __init__(self):
        self.messages = self

    def parse(self, **kw):
        text = kw["messages"][0]["content"]
        cid = text.split("CLAUSE ", 1)[1].split(":", 1)[0]
        clause = policy.clause_text(cid).split("\n", 1)[1]
        quote = " ".join(clause.split()[:8])
        w = InterpretationWire(clause_id=cid, verdict="compliant", cited_text=quote, rationale="dry run", missing_info="")
        return SimpleNamespace(parsed_output=w, stop_reason="end_turn", usage=SimpleNamespace(input_tokens=0, output_tokens=0))
