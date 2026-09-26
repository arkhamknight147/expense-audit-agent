"""LangGraph wiring: extract -> rules -> anomaly -> interpret -> decide -> [human_review] -> finalize
(T3.5, D2, ADR-021).

- Escalations pause in `human_review` via `interrupt()`; the run is checkpointed per claim
  (thread_id = claim_id) and resumed with `Command(resume=<auditor decision>)`.
- On resume LangGraph re-runs the human_review node from its start, so nothing before the
  interrupt() call has side effects; the audit event is written after it returns.
- State holds only JSON-serialisable data (evidence is stored as dicts).
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Any, Callable, Optional, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from . import policy
from .anomaly import AnomalySignal, detect
from .decide import ESCALATE, decide
from .interpret import interpret_claim
from .rules import LineEvidence, RuleResult, evaluate, evidence_from_extraction
from .store import append_event

# D4: allowed auditor actions and reason codes. Only a human can reject or partially approve.
REVIEW_ACTIONS = {
    "approve": {"policy_compliant_after_review", "exception_approved"},
    "reject": {"policy_violation_confirmed", "anomaly_confirmed", "duplicate_confirmed"},
    "partial_approve": {"over_limit_capped"},
    "return_to_employee": {"missing_info_requested", "wrong_category"},
}


class ClaimState(TypedDict, total=False):
    claim: dict
    ledger: list
    extractions: dict
    evidence: list
    rule_results: list
    anomalies: list
    interpretations: list
    decision: dict
    review: dict
    final_status: str


def validate_review(review: dict, claim_total: float) -> dict:
    action, reason = review.get("action"), review.get("reason_code")
    if action not in REVIEW_ACTIONS:
        raise ValueError(f"action must be one of {sorted(REVIEW_ACTIONS)}")
    if reason not in REVIEW_ACTIONS[action]:
        raise ValueError(f"reason_code for {action} must be one of {sorted(REVIEW_ACTIONS[action])}")
    if not review.get("reviewer"):
        raise ValueError("reviewer id is required")
    if action == "partial_approve":
        amt = float(review.get("approved_amount", -1))
        if not 0 < amt < claim_total:
            raise ValueError("partial_approve needs 0 < approved_amount < claim total")
    return review


def _ev(state: ClaimState) -> list[LineEvidence]:
    return [LineEvidence(**d) for d in state["evidence"]]


def _rr(state: ClaimState) -> list[RuleResult]:
    return [RuleResult(**d) for d in state["rule_results"]]


def build_graph(*, extract_fn: Callable[[str], dict], interpret_client: Any = None, db=None,
                checkpointer=None, mode: Optional[str] = None):
    """extract_fn(receipt_path) -> extraction result; db = sqlite connection for the audit log."""

    def log(state, actor, action, payload, reason=None):
        if db is not None:
            append_event(db, state["claim"]["claim_id"], actor, action, payload, reason)

    def extract_node(state: ClaimState):
        ex = {}
        for li in state["claim"]["line_items"]:
            if li.get("receipt"):
                ex[li["line_id"]] = extract_fn(li["receipt"])
        evidence = [asdict(evidence_from_extraction(li, ex.get(li["line_id"]))) for li in state["claim"]["line_items"]]
        log(state, "agent", "extracted", {lid: {"status": r["status"], "flags": r.get("flags", [])} for lid, r in ex.items()})
        return {"extractions": ex, "evidence": evidence}

    def rules_node(state: ClaimState):
        rr = evaluate(state["claim"], _ev(state), state.get("ledger", []))
        log(state, "agent", "rules_evaluated", {"non_pass": [r.as_dict() for r in rr if r.status != "pass"]})
        return {"rule_results": [r.as_dict() for r in rr]}

    def anomaly_node(state: ClaimState):
        an = detect(state["claim"], _ev(state), _rr(state))
        if an:
            log(state, "agent", "anomalies_detected", {"anomalies": [a.as_dict() for a in an]})
        return {"anomalies": [a.as_dict() for a in an]}

    def interpret_node(state: ClaimState):
        out = interpret_claim(state["claim"], _ev(state), _rr(state), client=interpret_client)
        if out:
            log(state, "agent", "clauses_interpreted",
                {"results": [{k: i[k] for k in ("clause_id", "line_id", "verdict", "agreement", "citations_valid")} for i in out]})
        return {"interpretations": out}

    def decide_node(state: ClaimState):
        kw = {"mode": mode} if mode else {}
        d = decide(state["claim"], _ev(state), _rr(state), [AnomalySignal(**a) for a in state["anomalies"]],
                   state["interpretations"], **kw)
        log(state, "agent", f"decision:{d['decision']}", {k: d[k] for k in ("decision", "reasons", "gates", "route", "mode")})
        return {"decision": d}

    def human_review_node(state: ClaimState):
        d = state["decision"]
        packet = {
            "claim_id": state["claim"]["claim_id"],
            "claim_total": d["claim_total"],
            "agent_recommendation": d["decision"] if d["show_recommendation_to_reviewer"] else "(hidden: shadow mode)",
            "reasons": d["reasons"] if d["show_recommendation_to_reviewer"] else [],
            "clauses": {cid: policy.clause_text(cid) for cid in d["clause_ids"]},
            "anomalies": state["anomalies"],  # auditor-only view (ADR-003)
            "interpretations": [{k: i[k] for k in ("clause_id", "verdict", "agreement")} | {"rationale": i["samples"][0]["rationale"],
                                "ask_employee": i["samples"][0]["missing_info"]} for i in state["interpretations"]],
            "receipts": [li.get("receipt") for li in state["claim"]["line_items"]],
            "allowed_actions": {k: sorted(v) for k, v in REVIEW_ACTIONS.items()},
        }
        review = validate_review(interrupt(packet), d["claim_total"])  # pauses here until resumed
        log(state, f"auditor:{review['reviewer']}", f"review:{review['action']}", review, review["reason_code"])
        return {"review": review, "final_status": review["action"]}

    def finalize_node(state: ClaimState):
        status = state.get("final_status") or state["decision"]["decision"]
        log(state, "agent", f"final:{status}", {"itc_tags": state["decision"]["itc_tags"]})
        return {"final_status": status}

    def route(state: ClaimState) -> str:
        return "human_review" if state["decision"]["route"] == "human_review" else "finalize"

    g = StateGraph(ClaimState)
    for name, fn in [("extract", extract_node), ("rules", rules_node), ("anomaly", anomaly_node),
                     ("interpret", interpret_node), ("decide", decide_node), ("human_review", human_review_node),
                     ("finalize", finalize_node)]:
        g.add_node(name, fn)
    g.add_edge(START, "extract")
    g.add_edge("extract", "rules")
    g.add_edge("rules", "anomaly")
    g.add_edge("anomaly", "interpret")
    g.add_edge("interpret", "decide")
    g.add_conditional_edges("decide", route, {"human_review": "human_review", "finalize": "finalize"})
    g.add_edge("human_review", "finalize")
    g.add_edge("finalize", END)
    return g.compile(checkpointer=checkpointer)


def sqlite_checkpointer(path: str):
    """Persistent checkpoints so a paused review survives restarts."""
    import sqlite3

    from langgraph.checkpoint.sqlite import SqliteSaver
    return SqliteSaver(sqlite3.connect(path, check_same_thread=False))
