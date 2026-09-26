# Rules-engine eval — dev_truth

Evidence source: **ground truth** (isolates rule logic from extraction errors, R6).

| Metric | Result | Target |
|---|---|---|
| Clean claims with NO fail/gap/cannot_evaluate | 294/294 (100.0%) | 100% |
| Clean claims with NO needs_judgement | 294/294 (100.0%) | 100% |
| Gap recall (objective gaps) | 28/28 (100.0%) | 100% |
| Judgement cases: grey clause flagged for review or objectively resolved | 28/28 (100.0%) | 100% |
| Judgement: objectively resolved by code (e.g. premium cab after 22:00) | 1 | — |
| Q2 hard-violation recall (all) | 84/84 (100.0%) | 100% |

| Q2 recall by clause | Result |
|---|---|
| AIR-01 | 5/5 |
| GEN-02 | 5/5 |
| GEN-03 | 6/6 |
| GEN-04 | 8/8 |
| GEN-05 | 7/7 |
| GEN-06 | 3/3 |
| HTL-01 | 25/25 |
| HTL-04 | 4/4 |
| MEAL-01 | 7/7 |
| MEAL-03 | 6/6 |
| MISC-01 | 5/5 |
| TRN-01 | 3/3 |

Unexpected extra fails: none
False-positive clean claims (first 20): none
