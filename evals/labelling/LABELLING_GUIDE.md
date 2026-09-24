# Labelling guide — judgement slice

**Who:** PM (Nish). **What:** the 40 grey cases in `judgement_cases.csv`. **Why:** these are the only cases whose correct answer needs judgement, so the PM owns the ground truth (ADR-008, V3).

> Private eval material. Never paste this guide, `GREY_CLAUSES.md` or your labels into an agent prompt.

## How to label one row

1. Read `scenario_summary`, then open the receipt image(s) listed in `receipts` (generate them first with `python scripts/generate_golden_set.py`).
2. Read the clause named in `candidate_clause` in `policy/POLICY.md`, plus any other clause that applies.
3. Fill the four columns:

| Column | Allowed values | Rule |
|---|---|---|
| `clause_verdict` | `compliant` · `non_compliant` · `unclear` | Your reading of the policy text **as written**, not what you think the policy should say |
| `expected_decision` | `auto_approve` · `return_to_employee` · `escalate` | If `over_cap` is TRUE, the answer is `escalate` whatever the verdict (gate G5). If the verdict is `unclear` or `non_compliant`, the answer is `escalate` (the agent never rejects, ADR-001). `auto_approve` only if the verdict is `compliant` and the claim is under the cap. |
| `violated_clause_ids` | e.g. `ENT-03` (semicolon-separated) | Only when the verdict is `non_compliant` |
| `reasoning` | 1–2 sentences | Cite the clause wording that decided it. The LLM judge (Q6) is calibrated against this. |

Leave `relabel_clause_verdict` empty for now.

## Worked example

| scenario_summary | clause_verdict | expected_decision | violated_clause_ids | reasoning |
|---|---|---|---|---|
| Hotel Fri+Sat nights. Justification: "Took personal leave Saturday-Sunday; business meeting on Monday." | `non_compliant` | `escalate` | `HTL-03` | HTL-03 allows weekend stays only if cheaper than returning or required by business; personal leave meets neither. |

## Consistency check (10% re-label)

One week after finishing, pick 4 rows at random, hide your first answers, and fill `relabel_clause_verdict` from scratch. If more than 1 of 4 differs, tighten the rule you used and note it in `docs/DECISIONS.md`.

## Time budget

About 2–3 minutes per row, so **~90 minutes** for all 40.
