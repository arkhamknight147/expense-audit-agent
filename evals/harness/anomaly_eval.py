"""Anomaly-check eval (T3.3, N5).

truth mode (free): false alarms on clean claims + data-only anomalies on ground-truth evidence.
real mode (~Rs 50): extraction -> rules -> anomaly on the dev anomaly + red-team slices, plus
false alarms on clean dev claims whose receipts are already cached (no extra cost).
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Callable

from expense_audit.anomaly import detect
from expense_audit.rules import FAIL, evaluate, evidence_from_extraction

from .rules_eval import GOLDEN, RESULTS, evidence_from_truth, load

TRUTH_DETECTABLE = {"cross_employee_duplicate", "gstin_state_mismatch"}


def _collect(claims, labels, ledger, evidence_fn: Callable) -> list[dict]:
    rows = []
    for c in claims:
        lab = labels[c["claim_id"]]
        evs = [evidence_fn(c, li, lab) for li in c["line_items"]]
        rr = evaluate(c, evs, ledger)
        an = detect(c, evs, rr)
        rows.append({"claim_id": c["claim_id"], "slice": lab["slice"], "subtype": lab["subtype"], "label": lab,
                     "anomalies": [a.as_dict() for a in an], "has_fail": any(r.status == FAIL for r in rr)})
    return rows


def score(rows: list[dict], mode: str) -> dict:
    m = defaultdict(lambda: [0, 0])
    false_alarms = []
    for r in rows:
        types = {a["type"] for a in r["anomalies"]}
        sl, st = r["slice"], r["subtype"]
        if sl in ("clean_under_cap", "over_cap_clean"):
            m["Clean claims with NO anomaly"][1] += 1
            if not types:
                m["Clean claims with NO anomaly"][0] += 1
            else:
                false_alarms.append((r["claim_id"], [a["evidence"] for a in r["anomalies"]][:2]))
        if sl == "judgement":
            m["Grey (legitimate-text) claims with NO injection alarm"][1] += 1
            if "prompt_injection" not in types:
                m["Grey (legitimate-text) claims with NO injection alarm"][0] += 1
            else:
                false_alarms.append((r["claim_id"], [a["evidence"] for a in r["anomalies"]][:2]))
        if sl == "anomaly" and (mode == "real" or st in TRUTH_DETECTABLE):
            k = f"Q8 anomaly detected: {st}"
            m[k][1] += 1
            if st in types or (st == "tampered_amount" and types & {"arithmetic_mismatch", "amount_mismatch"}) \
                    or (st == "gst_math_mismatch" and types & {"tax_rate_mismatch", "arithmetic_mismatch"}):
                m[k][0] += 1
        if sl == "red_team" and (mode == "real" or st == "justification"):
            k = f"Injection detected: {st}"
            m[k][1] += 1
            if "prompt_injection" in types:
                m[k][0] += 1
            m["Q9 proxy: red-team claims that would be escalated"][1] += 1
            if types or r["has_fail"]:
                m["Q9 proxy: red-team claims that would be escalated"][0] += 1
    return {"metrics": {k: {"hits": v[0], "total": v[1]} for k, v in sorted(m.items())}, "false_alarms": false_alarms[:20]}


def run_truth() -> dict:
    claims, labels, ledger = load("dev")
    fn = lambda c, li, lab: evidence_from_truth(li, lab["lines"][li["line_id"]]["truth"], c["trip"]["destination"])  # noqa: E731
    return score(_collect(claims, labels, ledger, fn), "truth")


def run_real(extract_fn: Callable[[str], dict], cached_only_fn: Callable[[str], bool]) -> dict:
    claims, labels, ledger = load("dev")
    chosen = []
    for c in claims:
        sl = labels[c["claim_id"]]["slice"]
        imgs = [li["receipt"] for li in c["line_items"] if li.get("receipt")]
        if sl in ("anomaly", "red_team") or (sl in ("clean_under_cap", "over_cap_clean") and imgs and all(map(cached_only_fn, imgs))):
            chosen.append(c)
    print(f"Anomaly eval (real): {len(chosen)} dev claims")
    cache = {}

    def fn(c, li, lab):
        ex = None
        if li.get("receipt"):
            ex = cache.get(li["receipt"]) or extract_fn(li["receipt"])
            cache[li["receipt"]] = ex
        return evidence_from_extraction(li, ex)
    return score(_collect(chosen, labels, ledger, fn), "real")


def write(summary: dict, tag: str) -> Path:
    RESULTS.mkdir(parents=True, exist_ok=True)
    src = "ground truth (data-only anomalies)" if tag.endswith("truth") else "real extraction (Sonnet)"
    lines = [f"# Anomaly eval — {tag}", "", f"Evidence source: **{src}**.", "", "| Metric | Result |", "|---|---|"]
    for k, v in summary["metrics"].items():
        lines.append(f"| {k} | {v['hits']}/{v['total']} |")
    lines += ["", f"False alarms (first 20): {summary['false_alarms'] or 'none'}"]
    md = RESULTS / f"anomaly_summary_{tag}.md"
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return md
