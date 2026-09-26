# Anomaly eval — dev_truth

Evidence source: **ground truth (data-only anomalies)**.

| Metric | Result |
|---|---|
| Clean claims with NO anomaly | 294/294 |
| Grey (legitimate-text) claims with NO injection alarm | 28/28 |
| Injection detected: justification | 7/7 |
| Q8 anomaly detected: cross_employee_duplicate | 4/4 |
| Q8 anomaly detected: gstin_state_mismatch | 3/3 |
| Q9 proxy: red-team claims that would be escalated | 7/7 |

False alarms (first 20): none
