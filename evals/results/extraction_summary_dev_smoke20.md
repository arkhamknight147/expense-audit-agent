# Extraction eval — dev_smoke20

Run: 20260926-143442 · Receipts: 20 · Fresh API calls: 20

| Metric | Result | Target |
|---|---|---|
| Q5 mean key-field accuracy | 88.0% | ≥95% |
| Q5 all 5 fields correct | 40.0% | — |
| Q7 first-pass valid | 45.0% | ≥95% |
| Q7 valid after retries | 50.0% | 100% |
| Cost per receipt | ₹1.025 | — |
| Latency p50 / p95 | 9.41s / 35.08s | — |
| Injection text captured in other_text | 1/1 | all |

| Field | Accuracy |
|---|---|
| vendor | 95.0% |
| invoice_date | 100.0% |
| total | 100.0% |
| vendor_gstin | 50.0% |
| category | 95.0% |

Top errors:
- (1×) vendor_gstin '27Z2ZIT3783Y1ZT' does not match the 15-character GSTIN format
- (1×) vendor_gstin '07Z2HIU7155C1ZU' does not match the 15-character GSTIN format
- (1×) bill_to_gstin '29Z2ACA2026M1Z7' does not match the 15-character GSTIN format


Misses by field: {'vendor_gstin': 10, 'category': 1, 'vendor': 1}
Raw results: `evals\results\extraction_dev_smoke20_20260926-143442.json` (git-ignored)
