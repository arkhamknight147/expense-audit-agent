# Extraction eval — dev_smoke20_haiku-4-5

Run: 20260926-151458 · Receipts: 20 · Fresh API calls: 20

| Metric | Result | Target |
|---|---|---|
| Q5 mean key-field accuracy | 88.0% | ≥95% |
| Q5 all 5 fields correct | 40.0% | — |
| Q7 first-pass valid | 100.0% | ≥95% |
| Q7 valid after retries | 100.0% | 100% |
| GSTIN passes checksum on first read | 45.0% | — |
| GSTIN still unverified after retry (flagged for human) | 11 | — |
| Cost per receipt | ₹0.8 | — |
| Latency p50 / p95 | 6.68s / 9.36s | — |
| Injection text captured in other_text | 1/1 | all |

| Field | Accuracy |
|---|---|
| vendor | 95.0% |
| invoice_date | 100.0% |
| total | 100.0% |
| vendor_gstin | 45.0% |
| category | 100.0% |

Top errors:


Misses by field: {'vendor_gstin': 11, 'vendor': 1}
Raw results: `evals\results\extraction_dev_smoke20_haiku-4-5_20260926-151458.json` (git-ignored)
