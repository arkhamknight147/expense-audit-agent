"""Extraction eval (Q5 key-field accuracy, Q7 schema validity) on the golden set.

Eval code may read labels; agent code (src/) never does (AGENTS.md rule 3).
"""
from __future__ import annotations

import json
import random
import re
import statistics
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = ROOT / "evals" / "golden"
RESULTS = ROOT / "evals" / "results"
FIELDS = ["vendor", "invoice_date", "total", "vendor_gstin", "category"]
CATEGORY_MAP = {"client_entertainment": "meal", "team_meal": "meal"}  # receipt-level category


def _norm(s) -> str:
    return re.sub(r"[^a-z0-9]", "", str(s or "").lower())


def score_fields(expected: dict, receipt: dict | None) -> dict[str, bool]:
    if not receipt:
        return {f: False for f in FIELDS}
    ev, xv = _norm(expected.get("vendor")), _norm(receipt.get("vendor_name"))
    exp_cat = CATEGORY_MAP.get(expected.get("category"), expected.get("category"))
    exp_total, got_total = expected.get("total"), receipt.get("total")
    return {
        "vendor": bool(ev and xv and (ev == xv or ev in xv or xv in ev)),
        "invoice_date": receipt.get("invoice_date") == expected.get("invoice_date"),
        "total": exp_total is not None and got_total is not None and abs(float(got_total) - float(exp_total)) <= 0.01,
        "vendor_gstin": (_norm(receipt.get("vendor_gstin")) == _norm(expected.get("vendor_gstin"))),
        "category": receipt.get("category") == exp_cat,
    }


def load_items(split: str = "dev") -> list[dict]:
    sp = json.loads((GOLDEN / "split.json").read_text(encoding="utf-8"))
    ids = set(sp[split])
    labels = {json.loads(l)["claim_id"]: json.loads(l) for l in open(GOLDEN / "labels.jsonl", encoding="utf-8")}
    items = []
    for line in open(GOLDEN / "claims.jsonl", encoding="utf-8"):
        c = json.loads(line)
        if c["claim_id"] not in ids:
            continue
        lab = labels[c["claim_id"]]
        for li in c["line_items"]:
            if not li.get("receipt"):
                continue
            ll = lab["lines"][li["line_id"]]
            items.append({"claim_id": c["claim_id"], "line_id": li["line_id"], "slice": lab["slice"],
                          "subtype": lab["subtype"], "image": li["receipt"],
                          "expected": ll["expected_fields"]})
    return items


def sample(items: list[dict], n: int, seed: int = 7) -> list[dict]:
    """Deterministic sample spread across receipt categories (for smoke runs)."""
    by_cat = defaultdict(list)
    for it in items:
        by_cat[CATEGORY_MAP.get(it["expected"]["category"], it["expected"]["category"])].append(it)
    rng = random.Random(seed)
    for v in by_cat.values():
        rng.shuffle(v)
    out, cats = [], sorted(by_cat)
    while len(out) < min(n, len(items)):
        for c in cats:
            if by_cat[c] and len(out) < n:
                out.append(by_cat[c].pop())
    return out


def run(items: list[dict], extract_fn: Callable[[str], dict], concurrency: int = 4) -> list[dict]:
    rows = []
    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        futs = {ex.submit(extract_fn, it["image"]): it for it in items}
        for i, fut in enumerate(as_completed(futs), 1):
            it = futs[fut]
            try:
                res = fut.result()
            except Exception as exc:  # one bad receipt must never kill the whole run
                res = {"status": "failed", "receipt": None, "errors": [f"harness_exception: {type(exc).__name__}: {str(exc)[:200]}"],
                       "flags": [], "first_pass_valid": False, "cost_usd": 0.0, "latency_s": 0.0, "cached": False}
            rows.append({**it, "result": res, "scores": score_fields(it["expected"], res.get("receipt"))})
            if i % 25 == 0 or i == len(items):
                print(f"  {i}/{len(items)} done")
    return rows


def summarise(rows: list[dict], usd_inr: float = 88.0) -> dict:
    n = len(rows)
    field_acc = {f: sum(r["scores"][f] for r in rows) / n for f in FIELDS}
    all_ok = sum(all(r["scores"].values()) for r in rows) / n
    first_pass = sum(r["result"].get("first_pass_valid", False) for r in rows) / n
    final_ok = sum(r["result"]["status"] == "ok" for r in rows) / n
    fresh = [r for r in rows if not r["result"].get("cached")]
    costs = [r["result"].get("cost_usd") or 0 for r in rows]
    lat = sorted(r["result"].get("latency_s", 0) for r in fresh) or [0]
    inj = [r for r in rows if r["slice"] == "red_team" and r["subtype"] in ("receipt_footer", "receipt_remarks")]
    inj_captured = sum(bool((r["result"].get("receipt") or {}).get("other_text")) for r in inj)
    misses = Counter(f for r in rows for f, ok in r["scores"].items() if not ok)
    return {
        "receipts": n,
        "Q5_field_accuracy": {k: round(v, 4) for k, v in field_acc.items()},
        "Q5_mean_field_accuracy": round(sum(field_acc.values()) / len(FIELDS), 4),
        "Q5_all_fields_correct": round(all_ok, 4),
        "Q7_first_pass_valid": round(first_pass, 4),
        "Q7_final_valid": round(final_ok, 4),
        "failed": sum(r["result"]["status"] != "ok" for r in rows),
        "cost_usd_total": round(sum(costs), 4),
        "cost_inr_per_receipt": round(sum(costs) / n * usd_inr, 3),
        "latency_p50_s": round(statistics.median(lat), 2),
        "latency_p95_s": round(lat[max(0, int(len(lat) * 0.95) - 1)], 2),
        "fresh_calls": len(fresh),
        "injection_text_captured_in_other_text": f"{inj_captured}/{len(inj)}",
        "gstin_first_pass_valid": round(sum(r["result"].get("gstin_first_pass_valid", True) for r in rows) / n, 4),
        "gstin_unverified_final": sum(any(f.startswith("gstin_unverified") for f in r["result"].get("flags", [])) for r in rows),
        "misses_by_field": dict(misses),
        "top_errors": Counter(e[:160] for r in rows for e in r["result"].get("errors", [])).most_common(3),
    }


def write_outputs(rows: list[dict], summary: dict, tag: str) -> tuple[Path, Path]:
    RESULTS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    raw = RESULTS / f"extraction_{tag}_{stamp}.json"
    raw.write_text(json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=1), encoding="utf-8")
    q5 = summary["Q5_mean_field_accuracy"]
    lines = [
        f"# Extraction eval — {tag}", "",
        f"Run: {stamp} · Receipts: {summary['receipts']} · Fresh API calls: {summary['fresh_calls']}", "",
    ]
    if summary["Q7_final_valid"] < 0.5:
        lines += ["> **RUN INVALID:** most extractions failed, so the accuracy numbers are meaningless. "
                  "Fix the top error below, then re-run.", ""]
    lines += [
        "| Metric | Result | Target |", "|---|---|---|",
        f"| Q5 mean key-field accuracy | {q5:.1%} | ≥95% |",
        f"| Q5 all 5 fields correct | {summary['Q5_all_fields_correct']:.1%} | — |",
        f"| Q7 first-pass valid | {summary['Q7_first_pass_valid']:.1%} | ≥95% |",
        f"| Q7 valid after retries | {summary['Q7_final_valid']:.1%} | 100% |",
        f"| GSTIN passes checksum on first read | {summary['gstin_first_pass_valid']:.1%} | — |",
        f"| GSTIN still unverified after retry (flagged for human) | {summary['gstin_unverified_final']} | — |",
        f"| Cost per receipt | ₹{summary['cost_inr_per_receipt']} | — |",
        f"| Latency p50 / p95 | {summary['latency_p50_s']}s / {summary['latency_p95_s']}s | — |",
        f"| Injection text captured in other_text | {summary['injection_text_captured_in_other_text']} | all |",
        "", "| Field | Accuracy |", "|---|---|",
    ] + [f"| {k} | {v:.1%} |" for k, v in summary["Q5_field_accuracy"].items()]
    lines += ["", "Top errors:"] + [f"- ({n}×) {e}" for e, n in summary["top_errors"]] + [""]
    lines += ["", f"Misses by field: {summary['misses_by_field']}", f"Raw results: `{raw.relative_to(ROOT)}` (git-ignored)"]
    md = RESULTS / f"extraction_summary_{tag}.md"
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return raw, md


def oracle_extract(items: list[dict]) -> Callable[[str], dict]:
    """Dry-run extractor that returns ground truth (tests the harness, costs nothing)."""
    by_img = {it["image"]: it["expected"] for it in items}

    def fn(image: str) -> dict:
        e = by_img[image]
        return {"status": "ok", "first_pass_valid": True, "cached": False, "cost_usd": 0.0, "latency_s": 0.0,
                "receipt": {"vendor_name": e["vendor"], "invoice_date": e["invoice_date"], "total": e["total"],
                            "vendor_gstin": e["vendor_gstin"],
                            "category": CATEGORY_MAP.get(e["category"], e["category"]), "other_text": []}}
    return fn
