# Extraction eval — dev_sample200_sonnet-5

Run: 20260926-210938 · Receipts: 200 · Fresh API calls: 6

| Metric | Result | Target |
|---|---|---|
| Q5 mean key-field accuracy | 97.9% | ≥95% |
| Q5 all 5 fields correct | 89.5% | — |
| Q7 first-pass valid | 98.5% | ≥95% |
| Q7 valid after retries | 99.5% | 100% |
| GSTIN passes checksum on first read | 99.5% | — |
| GSTIN still unverified after retry (flagged for human) | 0 | — |
| Cost per receipt | ₹1.569 | — |
| Latency p50 / p95 | 13.83s / 44.28s | — |
| Injection text captured in other_text | 4/4 | all |

| Field | Accuracy |
|---|---|
| vendor | 90.5% |
| invoice_date | 100.0% |
| total | 100.0% |
| vendor_gstin | 99.5% |
| category | 99.5% |

Top errors:
- (1×) api_or_parse_error: ValidationError: 1 validation error for ReceiptWire
  Invalid JSON: EOF while parsing a string at line 1 column 274 [type=json_invalid, inpu


Misses by field: {'category': 1, 'vendor': 19, 'vendor_gstin': 1}
Raw results: `evals\results\extraction_dev_sample200_sonnet-5_20260926-210938.json` (git-ignored)
