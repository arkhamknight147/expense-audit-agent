"""[3] ANOMALY CHECKS (T3.3, decisions N1-N5, ADR-019).

All checks are deterministic code. Any anomaly -> the claim is escalated (N4), labelled
"anomaly" (never "fraud") and shown to the auditor only (ADR-003).

N1 data checks: claimed vs receipt amount, printed arithmetic, tax above printed rate,
   GSTIN state vs vendor city, cross-employee duplicate, receipt date outside the trip.
N2 prompt-injection screen on receipt remarks and employee-written text. Known limit:
   keyword/regex screens miss reworded attacks; the code gates are the backstop (A2).
N3 no image forensics: a tampered total is caught when it no longer matches items + tax.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta
from functools import lru_cache
from typing import Optional

import yaml

from .config import POLICY_DIR
from .gstin import normalise as norm_gstin
from .rules import FAIL, LineEvidence, RuleResult

AMOUNT_TOLERANCE = 1.0  # rupees
DATE_TOLERANCE_DAYS = 1

# Generic instruction-like patterns aimed at a reviewer/system (N2). Kept deliberately
# generic; ADR-019 records that they were written after seeing the red-team set, so Q9 on
# that set is optimistic and a held-out paraphrased set is run in Phase 5.
INJECTION_PATTERNS = [
    r"\b(ignore|disregard|override|bypass)\b[^.]{0,40}\b(instruction|instructions|policy|policies|limit|limits|rules?|checks?)\b",
    r"\b(system|assistant|ai|auditor|reviewer|model)\s*[:,]",
    r"\b(note|message)\s+to\s+(the\s+)?(ai|assistant|auditor|reviewer|system)\b",
    r"\bpre-?approved\b",
    r"\bauto[_\s-]?approve",
    r"\b(admin|system)\s+override\b",
    r"\bmark(ed)?\s+(it\s+|this\s+)?(as\s+)?(approved|compliant|valid)\b",
    r"\bstatus\s*[:=]\s*approved\b",
    r"\bdo\s+not\s+(escalate|flag|review)\b",
    r"\bskip\s+(the\s+)?(human\s+)?(review|audit|checks?)\b",
    r"\bno\s+further\s+(checks?|review)\b",
    r"\b(output|return)\s+decision\b",
]
_INJ = [re.compile(p, re.I) for p in INJECTION_PATTERNS]


@dataclass
class AnomalySignal:
    type: str
    line_id: Optional[str]
    evidence: str

    def as_dict(self) -> dict:
        return self.__dict__.copy()


@lru_cache(maxsize=1)
def city_state_codes() -> dict[str, str]:
    data = yaml.safe_load((POLICY_DIR / "reference" / "city_state_codes.yaml").read_text(encoding="utf-8"))
    return {k.lower(): str(v).zfill(2) for k, v in data.items()}


def _d(s: Optional[str]) -> Optional[date]:
    try:
        return date.fromisoformat(s) if s else None
    except ValueError:
        return None


def injection_hits(text: str) -> list[str]:
    return [m.group(0) for rx in _INJ for m in [rx.search(text or "")] if m]


def detect(claim: dict, evidence: list[LineEvidence], rule_results: list[RuleResult] = ()) -> list[AnomalySignal]:
    out: list[AnomalySignal] = []
    start, end = _d(claim["trip"]["start_date"]), _d(claim["trip"]["end_date"])
    codes = city_state_codes()

    for ev in evidence:
        if not ev.extraction_ok:
            continue
        # claimed vs receipt amount
        if ev.has_receipt and ev.total is not None and ev.claimed_amount is not None \
                and abs(ev.claimed_amount - ev.total) > AMOUNT_TOLERANCE:
            out.append(AnomalySignal("amount_mismatch", ev.line_id,
                                     f"claimed {ev.claimed_amount} but receipt total is {ev.total}"))
        # printed arithmetic (catches a patched total, N3)
        if ev.itemised and ev.subtotal is not None and ev.total is not None and ev.taxes:
            tax_sum = sum(float(t.get("amount") or 0) for t in ev.taxes)
            if abs(ev.subtotal + tax_sum - ev.total) > AMOUNT_TOLERANCE:
                out.append(AnomalySignal("arithmetic_mismatch", ev.line_id,
                                         f"subtotal {ev.subtotal} + taxes {tax_sum:.2f} != total {ev.total}"))
        # tax charged above its printed rate
        if ev.subtotal:
            for t in ev.taxes:
                rate, amt = t.get("rate_pct"), t.get("amount")
                if rate and amt is not None and float(amt) > ev.subtotal * float(rate) / 100 * 1.02 + AMOUNT_TOLERANCE:
                    out.append(AnomalySignal("tax_rate_mismatch", ev.line_id,
                                             f"{t.get('label')}: charged {amt} > {rate}% of subtotal {ev.subtotal}"))
        # GSTIN state vs vendor city (only verified GSTINs, only known cities)
        g = norm_gstin(ev.vendor_gstin)
        city_code = codes.get((ev.vendor_city or "").strip().lower())
        if g and ev.vendor_gstin_valid is not False and city_code and g[:2] != city_code:
            out.append(AnomalySignal("gstin_state_mismatch", ev.line_id,
                                     f"vendor city {ev.vendor_city} is state {city_code} but GSTIN starts {g[:2]}"))
        # receipt date outside the trip
        d = _d(ev.invoice_date)
        if d and start and end and not (start - timedelta(days=DATE_TOLERANCE_DAYS) <= d <= end + timedelta(days=DATE_TOLERANCE_DAYS)):
            out.append(AnomalySignal("date_outside_trip", ev.line_id, f"receipt date {d} outside trip {start}..{end}"))
        # prompt injection in receipt text or employee-written text (N2)
        for source, texts in (("receipt", ev.other_text), ("employee_text", [ev.justification or ""])):
            for t in texts:
                hits = injection_hits(t)
                if hits:
                    out.append(AnomalySignal("prompt_injection", ev.line_id, f"{source}: {hits[:3]}"))
                    break

    for field in ("justification", "business_purpose"):
        hits = injection_hits(claim.get(field) or "")
        if hits:
            out.append(AnomalySignal("prompt_injection", None, f"claim {field}: {hits[:3]}"))

    # cross-employee duplicate (from the GEN-04 rule result)
    for r in rule_results:
        if r.clause_id == "GEN-04" and r.status == FAIL and "other employee" in r.detail:
            out.append(AnomalySignal("cross_employee_duplicate", r.line_id, r.detail))
    return out
