# Anomaly eval — dev_real

Evidence source: **real extraction (Sonnet)**.

| Metric | Result |
|---|---|
| Clean claims with NO anomaly | 36/36 |
| Injection detected: justification | 7/7 |
| Injection detected: receipt_footer | 7/7 |
| Injection detected: receipt_remarks | 7/7 |
| Q8 anomaly detected: cross_employee_duplicate | 4/4 |
| Q8 anomaly detected: gst_math_mismatch | 3/3 |
| Q8 anomaly detected: gstin_state_mismatch | 3/3 |
| Q8 anomaly detected: tampered_amount | 4/4 |
| Q9 proxy: red-team claims that would be escalated | 21/21 |

False alarms (first 20): none
