# Decision Log

Permanent product and architecture decisions. Each record says what was decided, why, what was rejected, and when to revisit it. New decisions are appended; superseded ones are marked, never deleted.

| ID | Decision | Status | Date |
|---|---|---|---|
| ADR-001 | No automatic rejection | Accepted | 2026-09-23 |
| ADR-002 | Automatic return-to-employee only for objective gaps | Accepted | 2026-09-23 |
| ADR-003 | Anomaly flags visible to the auditor only | Accepted | 2026-09-23 |
| ADR-004 | Auto-approve cap ₹5,000; 5% random post-audit | Accepted (starting values) | 2026-09-23 |
| ADR-005 | Partial approval stays human in the MVP | Accepted | 2026-09-23 |
| ADR-006 | Shadow-mode-first rollout | Accepted | 2026-09-23 |
| ADR-007 | Success metrics framework | Accepted | 2026-09-23 |
| ADR-008 | Eval plan design | Accepted | 2026-09-23 |
| ADR-009 | Policy corpus design | Accepted | 2026-09-23 |
| ADR-010 | Golden set generation | Accepted | 2026-09-24 |
| ADR-011 | LLM-assisted judgement labelling (supersedes ADR-008 V3 method) | Accepted | 2026-09-26 |
| ADR-012 | System architecture (A1–A10) | Accepted; A3 superseded by ADR-013 | 2026-09-26 |
| ADR-013 | Agent models: Anthropic Claude (supersedes ADR-012 A3) | Accepted | 2026-09-26 |
| ADR-014 | Secret management: three layers of protection | Accepted | 2026-09-26 |

---

## ADR-001: No automatic rejection

- **Decision:** The agent never rejects a claim. Rejection is always a human decision.
- **Why:** Errors are asymmetric. A wrong approval leaks money that post-audit can recover. A wrong rejection harms an employee and erodes trust in the system. Human final control is also a core principle of India's AI Governance Guidelines ("People First").
- **Rejected alternative:** Auto-reject high-confidence violations. Rejected because confidence is not calibrated enough to justify irreversible harm to people.
- **Revisit when:** Never for fraud-related rejections. Deterministic hard-limit breaches could be reconsidered after 3+ months of shadow data.
- **Ref:** PRD §3.3 A6.

## ADR-002: Automatic return-to-employee only for objective gaps

- **Decision:** The agent may send a claim back to the employee automatically, with a cited reason, only for objective and fixable gaps: missing receipt, no company GSTIN on the invoice, wrong category. If the employee contests, a human decides.
- **Why:** Reversible and low-harm, and it removes the biggest source of auditor back-and-forth.
- **Rejected alternative:** Route every gap to the auditor. Rejected because it wastes auditor time on clerical issues.
- **Revisit when:** Employee contest rate on automatic returns exceeds 10% (PRD §4.5 H3).
- **Ref:** PRD §3.3 A3.

## ADR-003: Anomaly flags visible to the auditor only

- **Decision:** Suspected fake or altered receipts are labelled "anomaly" (never "fraud") and shown only to the finance auditor, not to the approving manager.
- **Why:** An unverified suspicion shown to a manager can damage an employee unfairly. The flag is sensitive personal data under the DPDP regime, so access is limited to the role that needs it.
- **Rejected alternative:** Show the risk flag to the manager at approval time. Rejected because of the harm and privacy risk.
- **Revisit when:** Not planned.
- **Ref:** PRD §3.3 A7.

## ADR-004: Auto-approve cap ₹5,000; 5% random post-audit

- **Decision:** Claims above ₹5,000 are never auto-approved. 5% of claims that would be auto-approved go to a human reviewer instead.
- **Why:** Caps the exposure of each automatic decision. Random sampling keeps an unbiased check on auto-approval quality and feeds labelled data into evals. Anomaly checks apply at every amount, because fakes are pitched below thresholds.
- **Rejected alternative:** No cap, relying on confidence only. Rejected because model self-confidence is overconfident.
- **Revisit when:** Phase 4 eval results are available. Both values are starting assumptions.
- **Ref:** PRD §3.4 G5, G6.

## ADR-005: Partial approval stays human in the MVP

- **Decision:** The agent recommends reimbursing up to the policy limit, but a human confirms.
- **Why:** It changes the employee's payout, and there is no eval evidence yet.
- **Rejected alternative:** Auto-apply the cap. Deferred rather than rejected.
- **Revisit when:** Agreement with human decisions on partial approvals reaches ≥95% over ≥100 cases (PRD §4.5 H5).
- **Ref:** PRD §3.3 A5.

## ADR-006: Shadow-mode-first rollout

- **Decision:** Every new agent version (model, prompt or policy) runs in shadow mode (suggestions logged, not acted on) before it can act. Autonomy expands shadow → assisted → automatic for low-risk claims.
- **Why:** Autonomy is earned with evidence, and shadow data gives a direct comparison between human and agent decisions.
- **Rejected alternative:** Direct launch with automatic approval. Rejected because there is no evidence base yet.
- **Revisit when:** Not planned.
- **Ref:** PRD §3.5, §3.6.

## ADR-007: Success metrics framework

- **Decision:** (M1) North Star = verified audit coverage. (M2) False auto-approve rate ≤1% is the top release gate, with the golden set sized to support it statistically. (M3) Unit economics = total cost per claim including human review minutes; ≥80% of clean claims cleared with no human involvement. (M4) Anomaly detection reported as a baseline only in the MVP. (M5) Thresholds as listed in PRD §4, revisited after the baseline. (M6) The portfolio quotes offline metrics only.
- **Why:** Coverage × correctness can't be gamed by approving everything. Human minutes dominate cost, so escalation rate matters more than token price. Quoting pilot-style numbers from synthetic data would not be credible.
- **Rejected alternative:** Accuracy as the headline metric. Rejected because it hides the asymmetric cost of false approvals vs false escalations.
- **Revisit when:** Phase 4 baseline results are available.
- **Ref:** PRD §4.

## ADR-008: Eval plan design

- **Decision:** (V1) ~600-claim golden set with ~400 clean under-cap claims, so ≥300 are auto-approved and Q1 ≤1% is statistically supportable. (V2) Synthetic Indian receipts plus ~50 CORD receipts; SROIE excluded. (V3) PM hand-labels the ~40 judgement cases, with a labelling guide and a 10% re-label. (V4) 70/30 dev/test split, test set locked. (V5) Two baselines: rules-only and single strong model. (V6) Smoke subset per commit, full test set per release.
- **Why:** Corrects an earlier sizing error (Q1's denominator is auto-approved claims, not all claims). Licence-clean data only. The test set stays trustworthy only if it is not used for tuning.
- **Rejected alternative:** 300-claim set with Q1 restated as ≤2%. Rejected because the extra claims are code-generated and cheap.
- **Revisit when:** Actual E1 on the dev set differs materially from 80% (the auto-approved count, and so the statistical bound, changes with it).
- **Ref:** `docs/EVAL_PLAN.md`; PRD §4.3.

## ADR-009: Policy corpus design

- **Decision:** (P1) Every policy clause has a stable ID (e.g., `HTL-01`) used by citations, labels and the audit trail. (P2) `policy/limits.yaml` is the single source of truth; the rules engine reads it and `policy/POLICY.md` is generated from it by `scripts/build_policy.py`. (P3) Three grades: G1, G2, G3. (P4) X/Y/Z city tiers per the Government of India HRA classification. (P5) Limits as set in `limits.yaml` (synthetic assumptions). (P6) Seven deliberately grey clauses, recorded only in `evals/labelling/GREY_CLAUSES.md`, which is excluded from all agent context. (P7) Hotel invoices at or below ₹7,500 per night are tagged for tax team review, because commentary conflicts on whether recipients can claim ITC after GST 2.0.
- **Why:** Stable IDs make citations verifiable. A single source of truth prevents code/policy drift. Grey clauses are needed for the judgement slice, and hiding them keeps evals clean. Software should not encode a disputed tax position.
- **Rejected alternative:** Hand-written policy with limits duplicated in code. Rejected because of drift risk.
- **Revisit when:** The tax position on ITC for rooms ≤₹7,500 is clarified by an authoritative source (CBIC circular or ruling).
- **Ref:** `policy/limits.yaml`, `policy/POLICY.md`, `evals/labelling/GREY_CLAUSES.md`.

## ADR-010: Golden set generation

- **Decision:** (G0) Repo set up before generator code. (G1) Decisions labelled per claim, violations per line item. (G2) Receipts drawn with Pillow in 7 formats with seeded scan noise. (G3) Every receipt watermarked "SYNTHETIC SAMPLE - NOT A VALID INVOICE"; vendors and GSTINs fictitious. (G4) Images regenerated from a fixed seed and git-ignored; inputs (`claims.jsonl`, `ledger.jsonl`) and ground truth (`labels.jsonl`) in separate files. (G5) Stratified, seeded 70/30 split; test IDs locked. (G6) PM labels ~40 grey cases in a CSV. (G7) CORD receipts used for extraction only. (G8) Code-labelled slices first, PM labelling in parallel, CORD last.
- **Why:** Ground truth is assigned by construction, never by the rules engine under test. Watermarking prevents misuse of realistic synthetic receipts. Separating inputs from labels prevents leakage into the agent.
- **Rejected alternative:** Commit the images. Rejected because they are ~40 MB and fully reproducible from the seed.
- **Revisit when:** A real-world receipt source with a clear licence becomes available.
- **Ref:** `evals/generator/`, `scripts/generate_golden_set.py`, `evals/golden/MANIFEST.md`.

## ADR-011: LLM-assisted judgement labelling

- **Decision:** The 40 grey cases were labelled by an LLM (Gemini Pro) applying PM-written interpretation rules, with low-confidence cases flagged for PM review. The PM reviewed and owns the final labels. This supersedes the "PM hand-labels" method in ADR-008 (V3); the 10% PM re-label check still applies.
- **Why:** Time to ship. Hand-labelling was estimated at ~90 minutes; the PM-rules approach keeps the interpretation human-owned while cutting effort.
- **Risk accepted:** Labels may carry LLM bias, and agreement between the agent and these labels partly measures model-vs-model agreement. Mitigations: PM-written rules, PM review, the Q6 judge uses a different model family from the agent, and the method is disclosed in EVAL_PLAN §4.
- **Rejected alternative:** Fully manual labelling. Rejected on time.
- **Revisit when:** The 10% re-label shows more than 1 in 4 disagreements, or Q3/Q4 results look suspiciously high on the judgement slice.
- **Ref:** `evals/labelling/judgement_cases.csv`, `scripts/validate_judgement_labels.py`, EVAL_PLAN §4.

## ADR-012: System architecture

- **Decision:** (A1) LangGraph for orchestration, using `interrupt()` for human review. (A2) The LLM produces signals only; deterministic gate code makes every decision, and the agent has no approve or pay tool. (A3) Gemini Flash-Lite for receipt extraction; Gemini Flash (3 samples) for grey-clause interpretation only. (A4) Q6 judge on a different model family (GPT-OSS-120B via Groq). (A5) Clause lookup by ID from the `limits.yaml` registry; no vector database in the MVP. (A6) Pure-Python rules engine with pytest. (A7) SQLite for queue, audit log and checkpoints. (A8) Langfuse Hobby for tracing, cost and latency. (A9) Streamlit on Streamlit Community Cloud. (A10) Untrusted input kept as data, injection treated as an anomaly signal, code gates as backstop.
- **Why:** A2 means a fooled model cannot bypass the rule, cap or anomaly gates. A5: the policy is 26 clauses (~3k tokens), so a vector search adds latency and a failure mode with no recall gain. A9: community reports (June–Aug 2026) say new free Hugging Face Docker/Streamlit Spaces require PRO.
- **Rejected alternatives:** LLM makes the final decision (rejected: unsafe, untestable). Vector DB retrieval (deferred: optional later experiment against the same evals). Hugging Face Spaces (rejected: hosting cost).
- **Revisit when:** The policy corpus grows beyond what fits comfortably in context (reconsider A5), or free-tier limits block eval runs (reconsider A3/A4 providers).
- **Ref:** `docs/ARCHITECTURE.md`.

## ADR-013: Agent models on Anthropic Claude

- **Decision:** Replace Gemini with Anthropic Claude for the agent. Receipt extraction uses Claude Haiku 4.5 (vision + structured outputs); grey-clause interpretation uses Claude Sonnet 5 with 3 samples. The Q6 judge stays on GPT-OSS-120B via Groq (ADR-012 A4).
- **Why:** The PM already holds prepaid Anthropic credits, so there is no new spend and no free-tier rate limits. Side benefit: the agent (Claude), the labelling LLM (Gemini, ADR-011) and the judge (GPT-OSS) are now three different model families, which reduces the model-vs-model circularity risk.
- **Trade-off:** Higher per-token prices than Gemini Flash. Estimated LLM cost ≈ ₹0.5–1.5 per claim, so E2 (≤₹1.00) becomes tight; it is re-checked after the Phase 4 baseline (ADR-007 M5).
- **Rejected alternative:** Keep Gemini on the free tier. Rejected because of rate limits and because the PM prefers the existing Anthropic credits.
- **Revisit when:** E2 is missed after routing, or a cheaper model meets Q1–Q7.
- **Ref:** `.env.example`, `src/expense_audit/config.py`, `docs/ARCHITECTURE.md` §3, PRD §4.1.

## ADR-014: Secret management — three layers of protection

- **Decision:** API keys live only in a local `.env` file. Three independent layers stop a key reaching the public repo: (1) `.gitignore` excludes `.env`; (2) a dependency-free pre-commit hook (`scripts/check_secrets.py`) blocks commits containing key patterns or a `.env` file; (3) GitHub secret scanning with push protection rejects pushes containing known secret formats. Provider-side: one named key per project, a spend limit on the Anthropic workspace, and rotation if a leak is ever suspected.
- **Why:** The repo is public; a leaked key means direct financial loss. Each layer covers a different failure (forgotten ignore rule, key pasted into code, hook bypassed).
- **Rejected alternative:** Rely on `.gitignore` alone. Rejected because it does not catch keys pasted into source files.
- **Revisit when:** The project adds CI secrets (use GitHub Actions encrypted secrets) or deploys the demo (use Streamlit Cloud secrets).
- **Ref:** `.gitignore`, `.githooks/pre-commit`, `scripts/check_secrets.py`.
