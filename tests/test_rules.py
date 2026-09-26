"""Unit tests for the rules engine (T3.2). Hand-built claims, no API, no labels."""
from expense_audit import policy
from expense_audit.rules import CANNOT, FAIL, GAP, JUDGE, PASS, LineEvidence, evaluate

COMPANY = policy.config()["meta"]["company_gstin"]


def claim(grade="G1", dest="Mumbai", start="2026-11-09", end="2026-11-10", submitted="2026-11-15", sd_used=0, emp="E001"):
    return {"employee": {"id": emp, "grade": grade}, "trip": {"destination": dest, "start_date": start, "end_date": end},
            "submitted_date": submitted, "self_declarations_used_this_month": sd_used}


def hotel(rate=4000, bill_to=COMPANY, valid=True, extras=(), check_in="2026-11-09", nights=1, **kw):
    return LineEvidence(line_id="L1", claim_category="hotel", has_receipt=True, receipt_category="hotel",
                        total=rate * nights * 1.05, invoice_date="2026-11-10", vendor="Sai Residency", invoice_no="HTL/1",
                        payment_mode="Corporate card", itemised=True, item_descriptions=["Room - Deluxe", *extras],
                        bill_to_gstin=bill_to, bill_to_gstin_valid=valid, room_rate=rate, nights=nights, check_in=check_in, **kw)


def status(results, clause):
    return {r.status for r in results if r.clause_id == clause}


def test_hotel_within_and_over_limit():
    assert status(evaluate(claim(), [hotel(4500)]), "HTL-01") == {PASS}      # G1 X-city limit 4,500
    assert status(evaluate(claim(), [hotel(4550)]), "HTL-01") == {FAIL}


def test_hotel_invoice_gstin_gap_vs_unverified():
    assert status(evaluate(claim(), [hotel(bill_to=None)]), "HTL-02") == {GAP}
    assert status(evaluate(claim(), [hotel(bill_to="29ZZAXA2026M1ZX", valid=False)]), "HTL-02") == {CANNOT}  # never return on a misread


def test_minibar_and_weekend():
    assert status(evaluate(claim(), [hotel(extras=["Minibar"])]), "GEN-06") == {FAIL}
    r = evaluate(claim(start="2026-11-13", end="2026-11-15"), [hotel(check_in="2026-11-13", nights=2)])  # Fri+Sat
    assert status(r, "HTL-03") == {JUDGE}


def test_self_declaration_limits():
    sd = LineEvidence(line_id="L1", claim_category="local_transport", has_receipt=False, self_declared=True,
                      total=400, invoice_date="2026-11-09", payment_mode="Cash")
    assert status(evaluate(claim(sd_used=1), [sd]), "GEN-03") == {PASS}
    assert status(evaluate(claim(sd_used=2), [sd]), "GEN-03") == {FAIL}
    no_receipt = LineEvidence(line_id="L1", claim_category="meal", has_receipt=False, total=400, invoice_date="2026-11-09")
    assert status(evaluate(claim(), [no_receipt]), "GEN-03") == {GAP}


def test_failed_extraction_is_cannot_evaluate():
    ev = LineEvidence(line_id="L1", claim_category="meal", has_receipt=True, extraction_ok=False)
    assert any(r.status == CANNOT for r in evaluate(claim(), [ev]))


def test_business_class_rules():
    fl = lambda cls, mins: LineEvidence(line_id="L1", claim_category="flight", has_receipt=True, receipt_category="flight",
                                       total=15000, invoice_date="2026-11-20", flight_class=cls, flight_duration_min=mins,
                                       booked_on="2026-11-01", payment_mode="Corporate card")
    assert status(evaluate(claim(grade="G3"), [fl("Business", 300)]), "AIR-01") == {PASS}
    assert status(evaluate(claim(grade="G3"), [fl("Business", 150)]), "AIR-01") == {FAIL}
    assert status(evaluate(claim(grade="G2"), [fl("Business", 300)]), "AIR-01") == {FAIL}


def test_premium_cab_after_22_is_objective_pass():
    cab = lambda t: LineEvidence(line_id="L1", claim_category="local_transport", has_receipt=True, receipt_category="local_transport",
                                 total=600, invoice_date="2026-11-09", cab_vehicle="Sedan Prime", cab_time=t, payment_mode="UPI")
    assert status(evaluate(claim(), [cab("23:15")]), "TRN-02") == {PASS}
    assert status(evaluate(claim(), [cab("18:00")]), "TRN-02") == {JUDGE}


def test_duplicate_needs_same_invoice_number():
    meal = LineEvidence(line_id="L1", claim_category="connectivity", has_receipt=True, receipt_category="connectivity",
                        total=299.0, invoice_date="2026-11-09", vendor="NetLink Mobile", invoice_no="NLM/1", payment_mode="UPI")
    ledger_same = [{"ledger_id": "H1", "employee_id": "E009", "vendor": "NetLink Mobile", "invoice_no": "NLM/1",
                    "invoice_date": "2026-11-09", "amount": 299.0}]
    ledger_other_invoice = [{**ledger_same[0], "invoice_no": "NLM/2"}]
    assert status(evaluate(claim(), [meal], ledger_same), "GEN-04") == {FAIL}
    assert status(evaluate(claim(), [meal], ledger_other_invoice), "GEN-04") == set()  # a legit second ₹299 recharge


def test_category_mismatch_is_gap():
    ev = LineEvidence(line_id="L1", claim_category="meal", has_receipt=True, receipt_category="local_transport",
                      total=300, invoice_date="2026-11-09", payment_mode="UPI")
    assert any(r.status == GAP and r.check == "category_matches_receipt" for r in evaluate(claim(), [ev]))
