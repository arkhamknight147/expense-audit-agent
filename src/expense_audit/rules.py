"""[2] HARD RULES (T3.2, decisions R1-R6, ADR-018).

Deterministic checks, one function per `check` name in policy/limits.yaml. No LLM.

- R1: amounts, dates and items come from the RECEIPT (extracted evidence); the claim form
  supplies who/where/when (grade, destination, trip dates, submission date, attendees,
  self-declaration). Claim-vs-receipt differences are anomaly signals for T3.3.
- R2: every result is one of pass / fail / gap / cannot_evaluate / needs_judgement / not_applicable.
  `cannot_evaluate` (missing field, failed extraction, unverified GSTIN) must lead to escalation.
  `needs_judgement` marks the non-numeric part of a grey clause for interpretation (T3.4).
- R3: objective gaps (missing receipt, invoice not in company name, non-itemised meal bill,
  category mismatch) return `gap` -> return to employee. An unverified GSTIN is never a gap.
- R4: numeric parts of grey clauses are checked here; judgement parts go to T3.4.
- R5: duplicates are looked up in the read-only ledger.
"""
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Iterable, Optional

from . import policy
from .gstin import normalise as norm_gstin

PASS, FAIL, GAP, CANNOT, JUDGE, NA = "pass", "fail", "gap", "cannot_evaluate", "needs_judgement", "not_applicable"

ALCOHOL_WORDS = ("beer", "wine", "whisky", "whiskey", "malt", "vodka", "rum", "gin", "liquor", "brandy", "draught")
PREMIUM_CAB_WORDS = ("sedan", "suv", "prime", "premium", "luxury", "xl")
# claim-form category -> receipt-level category (client/team meals are restaurant bills)
CLAIM_TO_RECEIPT_CATEGORY = {"client_entertainment": "meal", "team_meal": "meal"}


@dataclass
class LineEvidence:
    """Normalised facts about one claim line, from the receipt (or the claim form if no receipt)."""
    line_id: str
    claim_category: str
    has_receipt: bool
    extraction_ok: bool = True
    self_declared: bool = False
    receipt_category: Optional[str] = None
    total: Optional[float] = None
    invoice_date: Optional[str] = None
    vendor: Optional[str] = None
    invoice_no: Optional[str] = None
    payment_mode: Optional[str] = None
    itemised: Optional[bool] = None
    item_descriptions: list[str] = field(default_factory=list)
    has_alcohol: Optional[bool] = None
    bill_to_gstin: Optional[str] = None
    bill_to_gstin_valid: Optional[bool] = None
    room_rate: Optional[float] = None
    nights: Optional[int] = None
    check_in: Optional[str] = None
    flight_class: Optional[str] = None
    flight_duration_min: Optional[int] = None
    booked_on: Optional[str] = None
    cab_vehicle: Optional[str] = None
    cab_time: Optional[str] = None
    attendees: list[str] = field(default_factory=list)


@dataclass
class RuleResult:
    clause_id: Optional[str]
    line_id: str
    status: str
    detail: str
    check: str

    def as_dict(self) -> dict:
        return self.__dict__.copy()


# ------------------------------------------------------------------ evidence builders
def _d(s: Optional[str]) -> Optional[date]:
    try:
        return date.fromisoformat(s) if s else None
    except ValueError:
        return None


def evidence_from_extraction(claim_line: dict, extraction: Optional[dict]) -> LineEvidence:
    """Build evidence from a claim line and its extraction result (extract.extract_receipt)."""
    ev = LineEvidence(line_id=claim_line["line_id"], claim_category=claim_line["category"],
                      has_receipt=bool(claim_line.get("receipt")), self_declared=bool(claim_line.get("self_declared")),
                      attendees=list(claim_line.get("attendees") or []))
    if not ev.has_receipt:
        ev.total = claim_line.get("amount_claimed")
        ev.invoice_date = claim_line.get("expense_date")
        ev.payment_mode = claim_line.get("payment_mode")
        return ev
    r = (extraction or {}).get("receipt")
    if not extraction or extraction.get("status") != "ok" or not r:
        ev.extraction_ok = False
        return ev
    items = [li.get("description") or "" for li in r.get("line_items") or []]
    tax_labels = [t.get("label") or "" for t in r.get("taxes") or []]
    text = " ".join(items + tax_labels).lower()
    hotel, flight, cab = r.get("hotel") or {}, r.get("flight") or {}, r.get("cab") or {}
    ev.receipt_category = r.get("category")
    ev.total = r.get("total")
    ev.invoice_date = r.get("invoice_date")
    ev.vendor = r.get("vendor_name")
    ev.invoice_no = r.get("invoice_no")
    ev.payment_mode = r.get("payment_mode")
    ev.itemised = r.get("itemised")
    ev.item_descriptions = items
    ev.has_alcohol = any(w in text for w in ALCOHOL_WORDS)
    ev.bill_to_gstin = r.get("bill_to_gstin")
    ev.bill_to_gstin_valid = r.get("bill_to_gstin_valid")
    ev.room_rate, ev.nights, ev.check_in = hotel.get("room_rate"), hotel.get("nights"), hotel.get("check_in")
    ev.flight_class = flight.get("travel_class")
    ev.flight_duration_min = flight.get("duration_minutes")
    ev.booked_on = flight.get("booked_on")
    ev.cab_vehicle, ev.cab_time = cab.get("vehicle_type"), cab.get("pickup_time") or r.get("invoice_time")
    return ev


# ------------------------------------------------------------------------ helpers
def _res(out: list, clause, ev_or_id, status, detail, check):
    lid = ev_or_id.line_id if isinstance(ev_or_id, LineEvidence) else ev_or_id
    out.append(RuleResult(clause, lid, status, detail, check))


def _norm(s) -> str:
    return re.sub(r"[^a-z0-9]", "", str(s or "").lower())


def _category(ev: LineEvidence) -> Optional[str]:
    """Receipt-level category (the evidence), falling back to the claim form without a receipt."""
    return ev.receipt_category or CLAIM_TO_RECEIPT_CATEGORY.get(ev.claim_category, ev.claim_category)


def _hhmm(s: Optional[str]) -> Optional[int]:
    m = re.match(r"^(\d{1,2}):(\d{2})", s or "")
    return int(m.group(1)) * 60 + int(m.group(2)) if m else None


# --------------------------------------------------------------------- the engine
def evaluate(claim: dict, evidence: list[LineEvidence], ledger: Iterable[dict] = ()) -> list[RuleResult]:
    L = policy.limits()
    cfg = policy.config()
    grade = claim["employee"]["grade"]
    dest = claim["trip"]["destination"]
    trip_start, trip_end = _d(claim["trip"]["start_date"]), _d(claim["trip"]["end_date"])
    trip_nights = (trip_end - trip_start).days if trip_start and trip_end else None
    submitted = _d(claim["submitted_date"])
    company_gstin = norm_gstin(cfg["meta"]["company_gstin"])
    non_reimbursable = [w.lower() for w in cfg["non_reimbursable_items"]]
    out: list[RuleResult] = []

    # Lines whose extraction failed cannot be checked at all -> escalate (R2).
    usable = []
    for ev in evidence:
        if ev.has_receipt and not ev.extraction_ok:
            _res(out, None, ev, CANNOT, "receipt extraction failed", "extraction")
        else:
            usable.append(ev)

    # R3: category mismatch between the claim form and the receipt.
    for ev in usable:
        if ev.has_receipt and ev.receipt_category:
            expected = CLAIM_TO_RECEIPT_CATEGORY.get(ev.claim_category, ev.claim_category)
            if expected != ev.receipt_category:
                _res(out, None, ev, GAP, f"claimed as '{ev.claim_category}' but receipt is '{ev.receipt_category}'",
                     "category_matches_receipt")

    # GEN-02 submission window
    for ev in usable:
        d = _d(ev.invoice_date)
        if not d or not submitted:
            _res(out, "GEN-02", ev, CANNOT, "expense or submission date missing", "within_submission_window")
            continue
        age = (submitted - d).days
        _res(out, "GEN-02", ev, PASS if age <= L["submission_window_days"] else FAIL,
             f"submitted {age} days after expense (max {L['submission_window_days']})", "within_submission_window")

    # GEN-03 receipts and self-declarations
    used = int(claim.get("self_declarations_used_this_month", 0))
    for ev in usable:
        if ev.has_receipt:
            continue
        if ev.self_declared:
            used += 1
            amt = ev.total or 0
            if amt > L["self_declaration_max_per_item"]:
                _res(out, "GEN-03", ev, FAIL, f"self-declared {amt:.0f} > {L['self_declaration_max_per_item']}",
                     "receipt_present_or_valid_self_declaration")
            elif used > L["self_declaration_max_per_month"]:
                _res(out, "GEN-03", ev, FAIL, f"self-declaration #{used} this month (max {L['self_declaration_max_per_month']})",
                     "receipt_present_or_valid_self_declaration")
            else:
                _res(out, "GEN-03", ev, PASS, "valid self-declaration", "receipt_present_or_valid_self_declaration")
        else:
            _res(out, "GEN-03", ev, GAP, "no receipt and no self-declaration", "receipt_present_or_valid_self_declaration")

    # GEN-04 duplicates (R5)
    ledger = list(ledger)
    for ev in usable:
        if not ev.has_receipt or ev.total is None:
            continue
        for h in ledger:
            same_amount = abs(float(h["amount"]) - float(ev.total)) <= 1.0
            same_date = h.get("invoice_date") == ev.invoice_date
            same_employee = h["employee_id"] == claim["employee"]["id"]
            inv_h, inv_e = _norm(h.get("invoice_no")), _norm(ev.invoice_no)
            if inv_h and inv_e:
                # Invoice number is the document identity (ADR-018): two ₹299 recharges from the
                # same telecom on the same day with different invoice numbers are NOT duplicates.
                same_doc = inv_h == inv_e
            else:
                # No invoice number to compare: fall back to vendor + date + amount, same employee only.
                vh, ve = _norm(h.get("vendor")), _norm(ev.vendor)
                same_doc = same_employee and bool(vh and ve and (vh in ve or ve in vh))
            if same_amount and same_date and same_doc:
                who = "same employee" if same_employee else f"other employee {h['employee_id']}"
                _res(out, "GEN-04", ev, FAIL, f"matches reimbursed {h['ledger_id']} ({who})", "not_duplicate")
                break

    # GEN-05 cash payments
    for ev in usable:
        if ev.total is not None and "cash" in (ev.payment_mode or "").lower() and ev.total > L["cash_single_payment_max"]:
            _res(out, "GEN-05", ev, FAIL, f"cash payment {ev.total} > {L['cash_single_payment_max']}", "cash_payment_within_limit")

    # GEN-06 non-reimbursable items
    for ev in usable:
        hits = [d for d in ev.item_descriptions if any(w in d.lower() for w in non_reimbursable)]
        if hits:
            _res(out, "GEN-06", ev, FAIL, f"non-reimbursable item(s): {hits}", "no_non_reimbursable_items")

    # Hotel rules
    for ev in usable:
        if _category(ev) != "hotel":
            continue
        lim = policy.hotel_limit(grade, dest)
        if ev.room_rate is None:
            _res(out, "HTL-01", ev, CANNOT, "room rate not found on invoice", "hotel_within_limit")
        else:
            _res(out, "HTL-01", ev, PASS if ev.room_rate <= lim else FAIL,
                 f"room rate {ev.room_rate:.0f} vs limit {lim} ({grade}, {policy.city_tier(dest)} city)", "hotel_within_limit")
        bt = norm_gstin(ev.bill_to_gstin)
        if not bt:
            _res(out, "HTL-02", ev, GAP, "invoice does not show the company GSTIN", "hotel_invoice_has_company_gstin")
        elif ev.bill_to_gstin_valid is False:
            _res(out, "HTL-02", ev, CANNOT, "bill-to GSTIN could not be verified (possible misread)", "hotel_invoice_has_company_gstin")
        elif bt != company_gstin:
            _res(out, "HTL-02", ev, GAP, "invoice billed to a different GSTIN", "hotel_invoice_has_company_gstin")
        else:
            _res(out, "HTL-02", ev, PASS, "company GSTIN on invoice", "hotel_invoice_has_company_gstin")
        ci = _d(ev.check_in) or trip_start
        nights = ev.nights or trip_nights or 0
        if ci and nights:
            weekend = [ci + timedelta(days=i) for i in range(nights) if (ci + timedelta(days=i)).weekday() in (4, 5)]
            if weekend:
                _res(out, "HTL-03", ev, JUDGE, f"stay includes Fri/Sat night(s) {[str(w) for w in weekend]}", "weekend_stay_screen")

    # HTL-04 laundry
    for ev in usable:
        if _category(ev) == "laundry":
            if trip_nights is None:
                _res(out, "HTL-04", ev, CANNOT, "trip dates missing", "laundry_allowed_for_trip_length")
            else:
                ok = trip_nights >= L["laundry_min_nights"]
                _res(out, "HTL-04", ev, PASS if ok else FAIL,
                     f"trip of {trip_nights} night(s) (laundry allowed from {L['laundry_min_nights']})", "laundry_allowed_for_trip_length")

    # Meals (routine meals only; client/team meals have their own caps)
    per_day = defaultdict(float)
    meal_lines = defaultdict(list)
    for ev in usable:
        if _category(ev) == "meal" and ev.claim_category == "meal":
            if ev.has_receipt and ev.itemised is False:
                _res(out, "MEAL-02", ev, GAP, "meal receipt is not itemised", "meal_receipt_itemised")
            if ev.has_alcohol:
                _res(out, "MEAL-03", ev, FAIL, "alcohol on a routine meal", "no_alcohol_on_routine_meals")
            if ev.total is not None and ev.invoice_date:
                per_day[ev.invoice_date] += ev.total
                meal_lines[ev.invoice_date].append(ev.line_id)
    ml = L["meals_per_day"][grade]
    for day, amt in per_day.items():
        _res(out, "MEAL-01", ",".join(meal_lines[day]), PASS if amt <= ml else FAIL,
             f"meals on {day}: {amt:.2f} vs daily limit {ml}", "meals_within_daily_limit")

    # Entertainment: numeric caps here, judgement to T3.4 (R4)
    for ev in usable:
        if ev.claim_category in ("client_entertainment", "team_meal") and ev.total is not None:
            heads = len(ev.attendees) + 1  # listed attendees + the claimant
            per_head = ev.total / heads
            if ev.claim_category == "client_entertainment":
                cap = L["client_entertainment_per_attendee"]
                _res(out, "ENT-01", ev, FAIL if per_head > cap else JUDGE,
                     f"{per_head:.0f} per attendee ({heads} people) vs cap {cap}; business purpose needs review",
                     "client_entertainment_within_cap")
                if ev.has_alcohol:
                    _res(out, "ENT-03", ev, JUDGE, "alcohol at client entertainment: reasonableness needs review",
                         "client_entertainment_within_cap")
            else:
                cap = L["team_meal_per_head"]
                _res(out, "ENT-02", ev, FAIL if per_head > cap else JUDGE,
                     f"{per_head:.0f} per head ({heads} people) vs cap {cap}; celebration/approval needs review",
                     "team_meal_within_cap")

    # Local transport daily limit + premium cabs
    tl = L["local_transport_per_day"][grade]
    per_day_t, t_lines = defaultdict(float), defaultdict(list)
    for ev in usable:
        if _category(ev) == "local_transport":
            if ev.total is not None and ev.invoice_date:
                per_day_t[ev.invoice_date] += ev.total
                t_lines[ev.invoice_date].append(ev.line_id)
            if ev.cab_vehicle and any(w in ev.cab_vehicle.lower() for w in PREMIUM_CAB_WORDS):
                mins = _hhmm(ev.cab_time)
                if mins is not None and mins >= L["late_night_after_hour"] * 60:
                    _res(out, "TRN-02", ev, PASS, f"premium cab at {ev.cab_time} (after {L['late_night_after_hour']}:00)", "premium_cab_screen")
                else:
                    _res(out, "TRN-02", ev, JUDGE, f"premium cab '{ev.cab_vehicle}' at {ev.cab_time or 'unknown time'}: necessity needs review",
                         "premium_cab_screen")
    for day, amt in per_day_t.items():
        if tl is None:
            _res(out, "TRN-01", ",".join(t_lines[day]), PASS, "no daily limit for grade", "local_transport_within_limit")
        else:
            _res(out, "TRN-01", ",".join(t_lines[day]), PASS if amt <= tl else FAIL,
                 f"local transport on {day}: {amt:.2f} vs daily limit {tl}", "local_transport_within_limit")

    # Air travel
    for ev in usable:
        if _category(ev) != "flight":
            continue
        cls = (ev.flight_class or "").lower()
        if not cls:
            _res(out, "AIR-01", ev, CANNOT, "travel class not found", "air_class_permitted")
        elif "business" in cls or "first" in cls:
            long_enough = (ev.flight_duration_min or 0) > L["business_class_min_flight_hours"] * 60
            ok = grade == "G3" and long_enough
            _res(out, "AIR-01", ev, PASS if ok else FAIL,
                 f"{ev.flight_class} for {grade}, duration {ev.flight_duration_min} min", "air_class_permitted")
        else:
            _res(out, "AIR-01", ev, PASS, f"{ev.flight_class}", "air_class_permitted")
        bo, dep = _d(ev.booked_on), _d(ev.invoice_date)
        if bo and dep:
            days = (dep - bo).days
            _res(out, "AIR-02", ev, PASS if days >= L["advance_booking_days"] else JUDGE,
                 f"booked {days} day(s) ahead (policy: {L['advance_booking_days']} where practicable)", "advance_booking_screen")

    # Connectivity per trip
    conn = [ev for ev in usable if _category(ev) == "connectivity" and ev.total is not None]
    if conn:
        tot = sum(ev.total for ev in conn)
        _res(out, "MISC-01", ",".join(ev.line_id for ev in conn), PASS if tot <= L["connectivity_per_trip"] else FAIL,
             f"connectivity {tot:.2f} vs {L['connectivity_per_trip']} per trip", "connectivity_within_limit")

    # Incidentals: always judgement
    for ev in usable:
        if _category(ev) == "incidental":
            _res(out, "MISC-02", ev, JUDGE, "incidental expense: necessity needs review", "incidental_screen")
    return out


def summarise(results: list[RuleResult]) -> dict:
    by = defaultdict(list)
    for r in results:
        by[r.status].append(r.as_dict())
    return {s: by.get(s, []) for s in (FAIL, GAP, CANNOT, JUDGE, PASS)}
