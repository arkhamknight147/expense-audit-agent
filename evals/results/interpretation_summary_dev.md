# Interpretation eval — dev

Evidence: ground truth. Model verdicts vs PM labels (dev judgement slice).

| Metric | Result | Target |
|---|---|---|
| Clause verdict agrees with PM | 7/28 | — |
| Final decision agrees with PM (I4b) | 15/28 | — |
| **False auto-approvals** (PM said not auto-approve) | 0  | 0 |
| Model 'compliant' where PM said otherwise | 0  | — |
| Citations valid (all samples) | 30/30 | 100% |
| Unanimous across 3 samples | 23/30 | — |
| Verdict 'unclear' | 23/30 | — |
| Cost | ₹47.08 total, ₹1.57 per line | — |

| PM label / model verdict | Count |
|---|---|
| PM compliant / model compliant | 3 |
| PM compliant / model resolved_by_code | 1 |
| PM compliant / model unclear | 13 |
| PM non_compliant / model non_compliant | 3 |
| PM non_compliant / model unclear | 8 |
