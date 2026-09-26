"""[6] DECIDE: the autonomy policy as ordered code (T3.5, D1, ADR-021).

The LLM never decides; this function does, using rule results, anomaly signals and
interpretation verdicts as inputs. Order (first match wins):
  1 cannot_evaluate (incl. failed extraction)          -> escalate
  2 any rule failure                                    -> escalate   (agent never rejects, A6)
  3 any anomaly                                         -> escalate   (auditor-only, ADR-003)
  4 any objective gap                                   -> return_to_employee (A3)
  5 grey clause not unanimously, validly 'compliant'    -> escalate   (I4b, ADR-020)
  6 claim total above the cap                           -> escalate   (G5)
  7 selected for the random post-audit sample           -> escalate   (G6)
  8 otherwise                                           -> auto_approve
D5 autonomy mode: 'auto' applies the decision; 'assisted' and 'shadow' send every claim to a
human ('shadow' hides the agent's recommendation from the reviewer, ADR-006 rollout ladder).
"""
from __future__ import annotations

import hashlib

from . import policy
from .config import AUTO_APPROVE_CAP, AUTONOMY_MODE, POST_AUDIT_SAMPLE_RATE
from .gstin import normalise as norm_gstin
from .rules import CANNOT, FAIL, GAP, JUDGE, LineEvidence

AUTO_APPROVE, RETURN, ESCALATE = "auto_approve", "return_to_employee", "escalate"
MODES = ("shadow", "assisted", "auto")


def in_random_audit(claim_id: str, rate: float = POST_AUDIT_SAMPLE_RATE) -> bool:
    """Deterministic, reproducible 5% sample (G6)."""
    return int(hashlib.sha256(claim_id.encode()).hexdigest(), 16) % 10_000 < int(rate * 10_000)


def itc_tag(ev: LineEvidence) -> str:
    """A9 ITC tag (tax team reviews in batches). Mirrors GST-01..03."""
    company = norm_gstin(policy.config()["meta"]["company_gstin"])
    cat = ev.receipt_category or ev.claim_category
    if cat in ("meal", "client_entertainment", "team_meal"):
        return "not_eligible"                                  # GST-02, s.17(5)
    if cat in ("hotel", "flight"):
        bt = norm_gstin(ev.bill_to_gstin)
        if not bt or bt != company:
            return "not_eligible"
        if ev.bill_to_gstin_valid is False:
            return "tax_review"
        if cat == "hotel" and (ev.room_rate is None or ev.room_rate <= policy.limits()["hotel_itc_review_threshold"]):
            return "tax_review"                                # GST-03 (contested position, ADR-009)
        return "eligible"
    return "na"


def decide(claim: dict, evidence: list[LineEvidence], rule_results: list, anomalies: list,
           interpretations: list[dict], mode: str = AUTONOMY_MODE) -> dict:
    assert mode in MODES, mode
    total = round(sum(li["amount_claimed"] for li in claim["line_items"]), 2)
    gates = {
        "G1_no_rule_failures": not any(r.status == FAIL for r in rule_results),
        "G2_all_evaluable": not any(r.status == CANNOT for r in rule_results),
        "G3_no_anomalies": not anomalies,
        "G4_grey_clauses_unanimous_compliant": True,
        "G5_under_cap": total <= AUTO_APPROVE_CAP,
        "G6_not_in_random_audit": not in_random_audit(claim["claim_id"]),
    }
    judged = {(i["line_id"], i["clause_id"]): i for i in interpretations}
    grey_open = []
    for r in rule_results:
        if r.status == JUDGE:
            i = judged.get((r.line_id, r.clause_id))
            if not (i and i["verdict"] == "compliant" and i["unanimous"] and i["citations_valid"]):
                grey_open.append(f"{r.clause_id} ({i['verdict'] if i else 'not interpreted'})")
    gates["G4_grey_clauses_unanimous_compliant"] = not grey_open

    def pick() -> tuple[str, list[str]]:
        if not gates["G2_all_evaluable"]:
            return ESCALATE, [f"cannot evaluate: {r.clause_id or r.check} {r.line_id} - {r.detail}" for r in rule_results if r.status == CANNOT]
        if not gates["G1_no_rule_failures"]:
            return ESCALATE, [f"{r.clause_id} {r.line_id}: {r.detail}" for r in rule_results if r.status == FAIL]
        if not gates["G3_no_anomalies"]:
            return ESCALATE, [f"anomaly {a.type} {a.line_id or ''}: {a.evidence}" for a in anomalies]
        gaps = [r for r in rule_results if r.status == GAP]
        if gaps:
            return RETURN, [f"{r.clause_id or r.check} {r.line_id}: {r.detail}" for r in gaps]
        if grey_open:
            return ESCALATE, [f"needs human judgement: {g}" for g in grey_open]
        if not gates["G5_under_cap"]:
            return ESCALATE, [f"claim total {total} above auto-approve cap {AUTO_APPROVE_CAP}"]
        if not gates["G6_not_in_random_audit"]:
            return ESCALATE, ["selected for random post-audit sample (5%)"]
        return AUTO_APPROVE, ["all gates passed"]

    decision, reasons = pick()
    clause_ids = sorted({r.clause_id for r in rule_results if r.clause_id and r.status in (FAIL, GAP, CANNOT, JUDGE)})
    return {
        "claim_id": claim["claim_id"], "decision": decision, "reasons": reasons, "gates": gates,
        "clause_ids": clause_ids, "claim_total": total, "mode": mode,
        "route": "human_review" if (decision == ESCALATE or mode != "auto") else decision,
        "show_recommendation_to_reviewer": mode != "shadow",
        "itc_tags": {ev.line_id: itc_tag(ev) for ev in evidence},
    }
