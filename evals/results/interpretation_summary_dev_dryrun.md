# Interpretation eval — dev_dryrun

Evidence: ground truth. Model verdicts vs PM labels (dev judgement slice).

| Metric | Result | Target |
|---|---|---|
| Clause verdict agrees with PM | 17/28 | — |
| Final decision agrees with PM (I4b) | 18/28 | — |
| **False auto-approvals** (PM said not auto-approve) | 10 ['C0522', 'C0524', 'C0526', 'C0529', 'C0532', 'C0536', 'C0537', 'C0550', 'C0557', 'C0559'] | 0 |
| Model 'compliant' where PM said otherwise | 11 [('C0522', 'HTL-03', 'non_compliant'), ('C0524', 'HTL-03', 'non_compliant'), ('C0526', 'HTL-03', 'non_compliant'), ('C0529', 'ENT-01', 'non_compliant'), ('C0532', 'ENT-01', 'non_compliant'), ('C0536', 'ENT-02', 'non_compliant'), ('C0537', 'ENT-02', 'non_compliant'), ('C0544', 'ENT-03', 'non_compliant'), ('C0550', 'TRN-02', 'non_compliant'), ('C0557', 'MISC-02', 'non_compliant'), ('C0559', 'MISC-02', 'non_compliant')] | — |
| Citations valid (all samples) | 30/30 | 100% |
| Unanimous across 3 samples | 30/30 | — |
| Verdict 'unclear' | 0/30 | — |
| Cost | ₹0.0 total, ₹0.0 per line | — |

| PM label / model verdict | Count |
|---|---|
| PM compliant / model compliant | 16 |
| PM compliant / model resolved_by_code | 1 |
| PM non_compliant / model compliant | 11 |
