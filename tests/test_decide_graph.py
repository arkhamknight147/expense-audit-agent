"""T3.5 tests: decision order, audit-log chain, and the LangGraph flow with pause/resume.
Fake extractor and fake model, no API cost."""
import sqlite3
from types import SimpleNamespace

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from expense_audit import interpret as I
from expense_audit import store
from expense_audit.anomaly import AnomalySignal
from expense_audit.decide import AUTO_APPROVE, ESCALATE, RETURN, decide, in_random_audit
from expense_audit.graph import build_graph, validate_review
from expense_audit.rules import CANNOT, FAIL, GAP, JUDGE, PASS, LineEvidence, RuleResult


def claim(cid="C9001", amount=315.0, receipt="r1.jpg", **kw):
    c = {"claim_id": cid, "employee": {"id": "E001", "name": "X", "grade": "G1", "base_city": "Mumbai"},
         "trip": {"destination": "Pune", "start_date": "2026-11-09", "end_date": "2026-11-09"},
         "business_purpose": "Client workshop", "submitted_date": "2026-11-15", "self_declarations_used_this_month": 0,
         "line_items": [{"line_id": "L1", "category": "meal", "expense_date": "2026-11-09", "amount_claimed": amount,
                         "payment_mode": "UPI", "description": "Meal", "self_declared": False, "receipt": receipt}]}
    c.update(kw)
    return c


def rr(*statuses):
    return [RuleResult("MEAL-01", "L1", s, "x", "chk") for s in statuses]


EV = [LineEvidence(line_id="L1", claim_category="meal", has_receipt=True, receipt_category="meal", total=315.0)]
OK_INTERP = {"line_id": "L1", "clause_id": "HTL-03", "verdict": "compliant", "unanimous": True, "citations_valid": True}


def first_non_audited(prefix="C"):
    return next(f"{prefix}{i:04d}" for i in range(1, 999) if not in_random_audit(f"{prefix}{i:04d}"))


@pytest.mark.parametrize("statuses,anoms,expected", [
    ((PASS,), [], AUTO_APPROVE),
    ((CANNOT, FAIL), [], ESCALATE),
    ((FAIL, GAP), [], ESCALATE),
    ((GAP,), [AnomalySignal("amount_mismatch", "L1", "x")], ESCALATE),
    ((GAP,), [], RETURN),
])
def test_decision_order(statuses, anoms, expected):
    assert decide(claim(first_non_audited()), EV, rr(*statuses), anoms, [], mode="auto")["decision"] == expected


def test_grey_clause_needs_unanimous_valid_compliant():
    c = claim(first_non_audited())
    grey = [RuleResult("HTL-03", "L1", JUDGE, "weekend", "weekend_stay_screen")]
    assert decide(c, EV, grey, [], [OK_INTERP], mode="auto")["decision"] == AUTO_APPROVE
    assert decide(c, EV, grey, [], [OK_INTERP | {"unanimous": False, "verdict": "unclear"}], mode="auto")["decision"] == ESCALATE
    assert decide(c, EV, grey, [], [], mode="auto")["decision"] == ESCALATE  # not interpreted -> human


def test_cap_random_audit_and_modes():
    assert decide(claim(first_non_audited(), amount=6000.0), EV, rr(PASS), [], [], mode="auto")["decision"] == ESCALATE
    audited = next(f"C{i:04d}" for i in range(1, 999) if in_random_audit(f"C{i:04d}"))
    d = decide(claim(audited), EV, rr(PASS), [], [], mode="auto")
    assert d["decision"] == ESCALATE and "random post-audit" in d["reasons"][0]
    s = decide(claim(first_non_audited()), EV, rr(PASS), [], [], mode="shadow")
    assert s["decision"] == AUTO_APPROVE and s["route"] == "human_review" and not s["show_recommendation_to_reviewer"]


def test_random_audit_rate_is_about_5_percent():
    n = sum(in_random_audit(f"C{i:05d}") for i in range(20000))
    assert 800 < n < 1200


def test_audit_log_is_hash_chained_and_tamper_evident(tmp_path):
    con = store.connect(tmp_path / "a.db")
    store.append_event(con, "C1", "agent", "decision:auto_approve", {"x": 1})
    store.append_event(con, "C1", "auditor:A1", "review:approve", {"y": 2}, "policy_compliant_after_review")
    assert store.verify_chain(con) == (True, None)
    con.execute("UPDATE audit_log SET payload='{\"x\": 999}' WHERE id=1")  # simulated tampering outside the app
    assert store.verify_chain(con) == (False, 1)


def test_review_validation():
    with pytest.raises(ValueError):
        validate_review({"action": "reject", "reason_code": "policy_compliant_after_review", "reviewer": "A1"}, 500)
    with pytest.raises(ValueError):
        validate_review({"action": "approve", "reason_code": "exception_approved"}, 500)  # no reviewer
    with pytest.raises(ValueError):
        validate_review({"action": "partial_approve", "reason_code": "over_limit_capped", "reviewer": "A1",
                         "approved_amount": 900}, 500)


def fake_extraction(total=315.0, printed_subtotal=300.0):
    receipt = {"readable": True, "document_type": "restaurant_bill", "category": "meal", "vendor_name": "Spice Trail Kitchen",
               "vendor_city": "Pune", "vendor_gstin": None, "bill_to_name": None, "bill_to_gstin": None, "invoice_no": "RST/1",
               "invoice_date": "2026-11-09", "invoice_time": "13:10", "itemised": True,
               "line_items": [{"description": "Veg Thali", "quantity": 1, "rate": 300, "amount": 300}],
               "subtotal": printed_subtotal, "taxes": [{"label": "CGST 2.5%", "rate_pct": 2.5, "amount": 7.5},
                                                        {"label": "SGST 2.5%", "rate_pct": 2.5, "amount": 7.5}],
               "total": total, "payment_mode": "UPI", "hotel": None, "flight": None, "cab": None, "other_text": [],
               "vendor_gstin_valid": None, "bill_to_gstin_valid": None}
    return lambda path: {"status": "ok", "receipt": receipt, "flags": []}


def test_graph_auto_approves_clean_claim(tmp_path):
    db = store.connect(tmp_path / "a.db")
    g = build_graph(extract_fn=fake_extraction(), db=db, checkpointer=InMemorySaver(), mode="auto")
    cid = first_non_audited()
    out = g.invoke({"claim": claim(cid), "ledger": []}, {"configurable": {"thread_id": cid}})
    assert out["final_status"] == AUTO_APPROVE
    actions = [e["action"] for e in store.events(db, cid)]
    assert actions[0] == "extracted" and actions[-1] == "final:auto_approve"
    assert store.verify_chain(db)[0]


def test_graph_pauses_for_human_and_resumes(tmp_path):
    db = store.connect(tmp_path / "a.db")
    g = build_graph(extract_fn=fake_extraction(total=598.0), db=db, checkpointer=InMemorySaver(), mode="auto")  # tampered total
    cid = first_non_audited()
    cfg = {"configurable": {"thread_id": cid}}
    out = g.invoke({"claim": claim(cid, amount=598.0), "ledger": []}, cfg)
    packet = out["__interrupt__"][0].value
    assert packet["agent_recommendation"] == ESCALATE and any(a["type"] == "arithmetic_mismatch" for a in packet["anomalies"])
    out2 = g.invoke(Command(resume={"action": "reject", "reason_code": "anomaly_confirmed", "reviewer": "A7"}), cfg)
    assert out2["final_status"] == "reject"
    ev = store.events(db, cid)
    assert [e for e in ev if e["action"] == "review:reject"][0]["actor"] == "auditor:A7"
    assert store.verify_chain(db)[0]


def test_terminal_review_prompt():
    import importlib.util
    from pathlib import Path
    spec = importlib.util.spec_from_file_location("run_claim", Path(__file__).resolve().parents[1] / "scripts" / "run_claim.py")
    rc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rc)
    from expense_audit.graph import REVIEW_ACTIONS
    packet = {"allowed_actions": {k: sorted(v) for k, v in REVIEW_ACTIONS.items()}}
    answers = iter(["2", "1", "A7", ""])  # reject / anomaly_confirmed
    review = rc.ask_review(packet, input_fn=lambda _: next(answers))
    assert review == {"action": "reject", "reason_code": "anomaly_confirmed", "reviewer": "A7"}
