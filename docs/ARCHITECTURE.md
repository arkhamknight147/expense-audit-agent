# Architecture — Expense Audit Agent

| Field | Value |
|---|---|
| Version | v1.0 |
| Status | **Approved** (A1–A10, 2026-09-26; A3 revised 2026-09-26). Decision records: `docs/DECISIONS.md` ADR-012, ADR-013 |
| Implements | PRD §3 Autonomy policy, §4 Success metrics; EVAL_PLAN |

## 1. Design principles

1. **The LLM produces signals; code makes decisions.** Extraction, clause interpretation and anomaly signals come from the LLM. Auto-approve / return / escalate is decided by deterministic gate code (PRD §3.4 G1–G6). The agent has no tool that can approve or pay (A11).
2. **Deterministic first.** Anything a rule can decide is decided by code reading `policy/limits.yaml`. The LLM is used only where interpretation is needed.
3. **Every decision is explainable and logged.** Each decision carries clause IDs and the exact policy text, and is written to an append-only audit log.
4. **Untrusted input stays data.** Receipt text and employee justifications are never treated as instructions.
5. **Cheapest model that meets the quality gate.** Route by task, verify by evals.

## 2. Claim flow

```
Claim (form + receipt images)
  │
  ▼
[1] EXTRACT ─────── per receipt: image → Pydantic schema (Claude Sonnet 5, ADR-017), ≤2 retries,
  │                 validation failures logged; low-confidence fields flagged
  ▼
[2] HARD RULES ──── code, one function per `check` in limits.yaml (HTL-01, MEAL-01, GEN-05 …)
  │
  ▼
[3] ANOMALY ─────── code: GST maths, GSTIN state vs city, ledger duplicates (same/other employee)
  │                 LLM signal: instruction-like text (prompt injection), visual tampering
  ▼
[4] CLAUSE LOOKUP ─ category → candidate clause IDs → exact clause text (by ID, no vector DB)
  │
  ▼
[5] INTERPRET ───── only for lines needing judgement: Claude Sonnet 5 ×3 samples;
  │                 agreement across samples = confidence (G4); must cite clause IDs
  ▼
[6] DECIDE ──────── code: gates G1–G6 + autonomy policy A1–A11
  │
  ├── auto_approve ──────────────► audit log
  ├── return_to_employee (cited) ─► audit log
  └── escalate ─► interrupt() ─► auditor reviews evidence + clauses ─► Command(resume=decision) ─► audit log
```

Step 3 and step 6 run on every claim, whatever the LLM says, so a fooled LLM cannot push a claim past the hard rules, the cap or an anomaly flag.

## 3. Components

| # | Component | Technology | Notes |
|---|---|---|---|
| A1 | Orchestration | LangGraph `StateGraph` | Human review via `interrupt()` + checkpointer; resume with `Command(resume=…)`. Pre-interrupt side effects must be idempotent (the node re-runs on resume). |
| A3 | Extraction model | Claude Sonnet 5 (vision + structured outputs) | Haiku 4.5 failed the GSTIN requirement (ADR-017); output validated again by our parser + GSTIN checksum |
| A3 | Interpretation model | Claude Sonnet 5, 3 samples | Only for grey/ambiguous lines (cost control) (ADR-013) |
| A4 | Eval judge (Q6) | GPT-OSS-120B via Groq (free tier) | Different model family from the agent (Claude) and from the labelling LLM (Gemini) |
| A5 | Policy lookup | `limits.yaml` clause registry + `POLICY.md` parsed by clause ID | No embeddings; citation validated against real clause text |
| A6 | Rules engine | Pure Python + pytest | Q2 target 100% |
| A7 | Storage | SQLite | Claim queue, append-only `audit_log`, LangGraph checkpoints |
| A8 | Observability | Langfuse (Hobby) | Trace per claim; tokens, cost, latency per node |
| A9 | Demo UI | Streamlit on Community Cloud | Auditor queue: evidence, receipt image and clause text side by side; reason code required |
| A10 | Injection defence | Delimited untrusted input + anomaly signal + code gates | Measured by Q9 |

## 4. Data contracts (summary)

| Object | Key fields |
|---|---|
| `ExtractedReceipt` | vendor, invoice_no, invoice_date, total, subtotal, taxes[], vendor_gstin, bill_to_gstin, category, line items[], payment_mode, field_confidence{} |
| `RuleResult` | clause_id, line_id, passed, detail |
| `AnomalySignal` | type (tampered_amount, duplicate, gst_math, gstin_state, prompt_injection), line_id, evidence |
| `Interpretation` | clause_id, verdict (compliant / non_compliant / unclear), cited_text, rationale, sample_agreement |
| `Decision` | decision, gate results G1–G6, reasons[], clause_ids[], itc_tags{}, model/prompt versions |
| `AuditEvent` | claim_id, timestamp, actor (agent / auditor id), action, reason_code, payload hash |

## 5. Repository layout

```
src/expense_audit/
  config.py        paths, env, model names
  policy.py        limits.yaml loader, city tiers, clause text by ID
  schemas.py       Pydantic models (section 4)
  extract.py       [1] receipt extraction
  rules.py         [2] hard-rule checks
  anomaly.py       [3] anomaly checks
  interpret.py     [4]+[5] clause lookup and interpretation
  decide.py        [6] gates
  graph.py         LangGraph wiring + interrupt
  store.py         SQLite: queue, audit log, checkpoints
app/               Streamlit auditor UI
evals/             generator, golden set, labelling, harness, results
tests/             unit tests
```

## 6. Security & privacy

- Secrets only in `.env` (git-ignored) and in the Streamlit Cloud secrets store; `.env.example` lists names only. Three layers stop a key reaching GitHub: `.gitignore`, a local pre-commit secret scan (`scripts/check_secrets.py`), and GitHub push protection (ADR-014).
- All data is synthetic. If real receipts were ever used, receipts would be personal data under the DPDP regime: purpose limitation, access control (anomaly flags visible to auditors only, ADR-003) and breach handling would apply.
- Least privilege: the agent has no payment or approval tool; API keys scoped per provider.

## 7. Known limits

- Anthropic API usage is paid from prepaid credits; Groq free-tier limits cap judge throughput. Full eval runs may need batching.
- Streamlit Community Cloud apps sleep when idle; the first load after sleep is slow.
- The deterministic clause lookup relies on correct category extraction; category errors are measured by Q5.
