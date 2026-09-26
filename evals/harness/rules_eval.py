"""Rules-engine eval (T3.2, R6): run the rules on GROUND-TRUTH evidence first, so rule bugs are
separated from extraction errors. Later the same scoring runs on real extraction output.
Eval code may read labels; agent code never does (AGENTS.md rule 3).
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

from expense_audit import policy
from expense_audit.rules import CANNOT, FAIL, GAP, JUDGE, PASS, LineEvidence, evaluate

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = ROOT / "evals" / "golden"
RESULTS = ROOT / "evals" / "results"
CAT = {"client_entertainment": "meal", "team_meal": "meal"}


def evidence_from_truth(claim_line: dict, truth: dict) -> LineEvidence:
    """Oracle evidence built from ground truth (what a perfect extractor would return)."""
    ev = LineEvidence(line_id=claim_line["line_id"], claim_category=claim_line["category"],
                      has_receipt=bool(claim_line.get("receipt")), self_declared=bool(claim_line.get("self_declared")),
                      attendees=list(claim_line.get("attendees") or []))
    if not ev.has_receipt:
        ev.total, ev.invoice_date, ev.payment_mode = claim_line["amount_claimed"], claim_line["expense_date"], claim_line["payment_mode"]
        return ev
    company = policy.config()["meta"]["company_gstin"]
    ev.receipt_category = CAT.get(truth["category"], truth["category"])
    ev.total, ev.invoice_date = truth["total"], truth["invoice_date"]
    ev.vendor, ev.invoice_no, ev.payment_mode = truth.get("vendor"), truth.get("invoice_no"), truth.get("payment_mode")
    ev.itemised = truth.get("itemised", True)
    ev.has_alcohol = bool(truth.get("alcohol"))
    if truth["category"] == "hotel":
        ev.item_descriptions = ["Room - Deluxe"] + list(truth.get("extras", []))
        ev.room_rate, ev.nights, ev.check_in = truth["room_rate"], truth["nights"], truth["check_in"]
    if truth["category"] in ("hotel", "flight"):
        ev.bill_to_gstin = company if truth.get("bill_to_company_gstin") else None
        ev.bill_to_gstin_valid = True if ev.bill_to_gstin else None
    if truth["category"] == "flight":
        ev.flight_class = truth["class"]
        ev.flight_duration_min = int(round(truth["duration_h"] * 60))
        ev.booked_on = truth["booked_on"]
    if truth["category"] == "local_transport":
        ev.cab_vehicle, ev.cab_time = truth.get("vehicle"), truth.get("time")
    return ev


def load(split: str = "dev"):
    ids = set(json.loads((GOLDEN / "split.json").read_text(encoding="utf-8"))[split])
    claims = [c for c in map(json.loads, open(GOLDEN / "claims.jsonl", encoding="utf-8")) if c["claim_id"] in ids]
    labels = {l["claim_id"]: l for l in map(json.loads, open(GOLDEN / "labels.jsonl", encoding="utf-8"))}
    ledger = [json.loads(l) for l in open(GOLDEN / "ledger.jsonl", encoding="utf-8")]
    return claims, labels, ledger


def run_truth(split: str = "dev") -> tuple[dict, list[dict]]:
    claims, labels, ledger = load(split)
    rows = []
    for c in claims:
        lab = labels[c["claim_id"]]
        evs = [evidence_from_truth(li, lab["lines"][li["line_id"]]["truth"]) for li in c["line_items"]]
        res = evaluate(c, evs, ledger)
        rows.append({"claim_id": c["claim_id"], "slice": lab["slice"], "subtype": lab["subtype"], "label": lab,
                     "results": [r.as_dict() for r in res]})
    return score(rows), rows


def score(rows: list[dict]) -> dict:
    m = defaultdict(lambda: [0, 0])  # name -> [hits, total]
    unexpected = Counter()
    fp_claims = []
    for r in rows:
        st = defaultdict(set)
        for x in r["results"]:
            st[x["status"]].add(x["clause_id"] or x["check"])
        lab, sl = r["label"], r["slice"]
        exp_v = {v["clause_id"] for v in lab["violations"]}
        if sl in ("hard_violation", "red_team") or (sl == "anomaly" and exp_v):
            for cid in exp_v:
                m[f"Q2 recall {cid}"][1] += 1
                m["Q2 hard-violation recall (all)"][1] += 1
                if cid in st[FAIL]:
                    m[f"Q2 recall {cid}"][0] += 1
                    m["Q2 hard-violation recall (all)"][0] += 1
            for extra in st[FAIL] - exp_v:
                unexpected[f"{sl}:{extra}"] += 1
        if sl in ("clean_under_cap", "over_cap_clean"):
            m["Clean claims with NO fail/gap/cannot_evaluate"][1] += 1
            m["Clean claims with NO needs_judgement"][1] += 1
            bad = st[FAIL] | st[GAP] | st[CANNOT]
            if not bad:
                m["Clean claims with NO fail/gap/cannot_evaluate"][0] += 1
            else:
                fp_claims.append((r["claim_id"], sorted(bad)))
            if not st[JUDGE]:
                m["Clean claims with NO needs_judgement"][0] += 1
        if sl == "objective_gap":
            g = lab["gaps"][0]
            key = g["clause_id"] or "category_matches_receipt"
            m["Gap recall (objective gaps)"][1] += 1
            if key in st[GAP]:
                m["Gap recall (objective gaps)"][0] += 1
            for extra in st[FAIL]:
                unexpected[f"objective_gap:{extra}"] += 1
        if sl == "judgement":
            k = "Judgement cases: grey clause flagged for review or objectively resolved"
            m[k][1] += 1
            if lab["grey_clause"] in (st[JUDGE] | st[FAIL]):
                m[k][0] += 1
            elif lab["grey_clause"] in st[PASS]:
                m[k][0] += 1
                m["Judgement: objectively resolved by code (e.g. premium cab after 22:00)"][0] += 1
    return {"metrics": {k: {"hits": v[0], "total": v[1], "rate": round(v[0] / v[1], 4) if v[1] else None}
                        for k, v in sorted(m.items())},
            "unexpected_fails": dict(unexpected), "false_positive_clean_claims": fp_claims[:20]}


def write(summary: dict, tag: str) -> Path:
    RESULTS.mkdir(parents=True, exist_ok=True)
    lines = [f"# Rules-engine eval — {tag}", "",
             "Evidence source: **ground truth** (isolates rule logic from extraction errors, R6).", "",
             "| Metric | Result | Target |", "|---|---|---|"]
    targets = {"Q2 hard-violation recall (all)": "100%", "Clean claims with NO fail/gap/cannot_evaluate": "100%",
               "Clean claims with NO needs_judgement": "100%", "Gap recall (objective gaps)": "100%",
               "Judgement cases: grey clause flagged for review or objectively resolved": "100%"}
    for k, v in summary["metrics"].items():
        if not k.startswith("Q2 recall "):
            shown = f"{v['hits']}/{v['total']} ({v['rate']:.1%})" if v["total"] else f"{v['hits']}"
            lines.append(f"| {k} | {shown} | {targets.get(k, '—')} |")
    lines += ["", "| Q2 recall by clause | Result |", "|---|---|"]
    for k, v in summary["metrics"].items():
        if k.startswith("Q2 recall "):
            lines.append(f"| {k.replace('Q2 recall ', '')} | {v['hits']}/{v['total']} |")
    lines += ["", f"Unexpected extra fails: {summary['unexpected_fails'] or 'none'}",
              f"False-positive clean claims (first 20): {summary['false_positive_clean_claims'] or 'none'}"]
    md = RESULTS / f"rules_summary_{tag}.md"
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return md
