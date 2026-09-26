# Extraction eval — dev_smoke20_sonnet-5

Run: 20260926-152217 · Receipts: 20 · Fresh API calls: 20

| Metric | Result | Target |
|---|---|---|
| Q5 mean key-field accuracy | 97.0% | ≥95% |
| Q5 all 5 fields correct | 85.0% | — |
| Q7 first-pass valid | 100.0% | ≥95% |
| Q7 valid after retries | 100.0% | 100% |
| GSTIN passes checksum on first read | 100.0% | — |
| GSTIN still unverified after retry (flagged for human) | 0 | — |
| Cost per receipt | ₹1.441 | — |
| Latency p50 / p95 | 6.24s / 18.8s | — |
| Injection text captured in other_text | 1/1 | all |

| Field | Accuracy |
|---|---|
| vendor | 90.0% |
| invoice_date | 100.0% |
| total | 100.0% |
| vendor_gstin | 100.0% |
| category | 95.0% |

Top errors:


Misses by field: {'category': 1, 'vendor': 2}
Raw results: `evals\results\extraction_dev_smoke20_sonnet-5_20260926-152217.json` (git-ignored)
