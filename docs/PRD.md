# PRD — Expense Audit Agent (working name)

| Field | Value |
|---|---|
| Version | v0.3.1 — Problem, Users, Autonomy policy, Success metrics |
| Status | Draft for review |
| Owner | Nish (PM) |
| Last updated | 2026-09-23 |
| Companion docs | `docs/EVAL_PLAN.md` · `docs/DECISIONS.md` |

> **Scenario:** A fictional mid-size Indian company, *Acme India Pvt Ltd* (~3,000 employees, multi-city, GST-registered), processes employee travel & expense (T&E) claims in INR. All company data in this project is synthetic. All market evidence is cited.

---

## 1. Problem

### 1.1 The true problem

The visible symptom is "expense reports are slow and annoying". That is not the problem worth solving.

**The true problem:** Finance teams face a forced trade-off between **audit coverage, audit cost, and reimbursement speed**. Checking a claim means a human reading unstructured evidence (receipts, invoices) against a text policy. That does not scale, so teams audit only a sample. Non-compliant and fraudulent claims pass through unchecked, while compliant employees still wait.

| Layer | Statement |
|---|---|
| Symptom | Claims take long to reimburse; employees resubmit; finance is overloaded |
| Cause | Every claim needs a manual policy check on unstructured documents |
| Root cause | Policy verification has needed human reading. Only humans could map a messy receipt to a text policy clause. |
| Consequence | Teams sample 10–20% of transactions [S5], so ~80%+ of spend is never checked. Detection relies on tips, not monitoring [S1]. |

**Problem statement:**
> Finance auditors at mid-size Indian companies can only verify a fraction of T&E claims against policy. Leakage (fraud, policy violations, lost GST credit) goes undetected, and compliant employees wait longer than necessary for reimbursement.

**Why this problem is suited to an agent (and where it is not):** reading receipts and interpreting policy text are language tasks where LLMs are now cheap and capable. Hard numeric limits (e.g., "hotel ≤ ₹6,000/night in Tier-2 cities") are **not** an LLM job. They belong in a deterministic rules engine. The agent's job is to **expand coverage to 100% and direct scarce auditor attention to the riskiest claims**, not to replace the auditor.

### 1.2 How do we know it is a true problem? (Evidence)

| # | Evidence | Figure | Strength | Source |
|---|---|---|---|---|
| E1 | Organisations lose revenue to occupational fraud | ~5% of revenue; median loss $145k per case; median scheme runs 12 months (1,921 cases, 138 countries) | **Strong** (independent, large sample) | [S1] |
| E2 | Fraud is found by tips, rarely by monitoring | Tips 43% of detections; automated data monitoring only 3%. Proactive data monitoring is associated with ~50% lower losses and ~50% shorter duration. | **Strong** | [S1] |
| E3 | Manual expense processing is costly and error-prone | $58 and 20 min per report; 19% contain errors; each fix costs $52 and 18 min | **Medium.** Credible body, but 2015 US data, so directional for India. | [S2] |
| E4 | Audit is sampled, not complete | Manual practices audit only 10–20% of expense transactions | **Weak–Medium** (vendor claim) | [S5] |
| E5 | Fake receipts have become trivial to produce | AI-generated receipts rose from 0% (Mar 2025) to 70.8% (May 2026) of flagged fraudulent receipts on AppZen's platform | **Medium** (single vendor's platform data, widely reported) | [S3], [S4] |
| E6 | Employees admit to it | 34% of 2,000 US/UK workers surveyed admitted using AI to generate fake receipts | **Medium** (vendor survey, Emburse) | [S4] |
| E7 | Finance buyers already prioritise this category | 59% of finance functions use AI in 2025; AP automation (37%) and error/anomaly detection (34%) are top-3 use cases | **Strong** (Gartner) | [S6] |

**Honest caveats:**
- **E5 is disputed in magnitude.** Inscribe reports AI makes up <5% of *lending* document fraud. The two figures measure different populations (expense receipts vs loan documents), so the direction ("rising fast for receipts") holds but the exact share should not be over-quoted. [S7]
- **India-specific primary data is thin.** Almost all quantified evidence is US/UK/global. This is the biggest evidence gap in this PRD (see §5).

### 1.3 Why solve it now?

| Driver | What changed | Source |
|---|---|---|
| Threat shift | Generative AI made fake receipts nearly free to produce. Visual inspection of a sample no longer catches them. | [S3], [S4] |
| Cost of the solution collapsed | LLM inference cost for equivalent capability has been falling ~10x per year, so an LLM check on *every* claim now costs paise, not rupees | [S8] |
| Buyer readiness | Finance leaders already adopt AI for AP and anomaly detection | [S6] |
| India regulation | The DPDP Rules were notified on 13 Nov 2025. Substantive obligations (consent, security safeguards, breach notification) apply from ~May 2027, with penalties up to ₹250 crore. Receipts contain personal data, so a new tool built now must be privacy-by-design. | [S9] |
| India tax | GST input tax credit (ITC) requires a valid tax invoice. Some T&E categories (e.g., food & beverages, vacation travel benefits) are blocked credits under Sec 17(5), CGST Act. Misclassified or non-compliant invoices mean lost or wrongly claimed credit. | [S10], [S11] |

### 1.4 Impact of not solving it

| For | Impact | Basis |
|---|---|---|
| Business | Leakage continues in the ~80–90% of claims never audited, and fraud runs a median 12 months before detection | [S1], [S5] |
| Business | Rework cost: ~1 in 5 reports needs a correction cycle | [S2] |
| Business | Lost or wrongly claimed GST ITC. The first creates a cash cost; the second a compliance exposure. | [S10], [S11] |
| Business | Future privacy exposure if receipt data is handled ad hoc once DPDP obligations apply | [S9] |
| Employees | Slower reimbursement, and honest employees pay the "tax" of controls designed for the dishonest few | Hypothesis H3 (to validate) |
| Auditors | Time spent on low-risk claims instead of high-risk ones; burnout from repetitive checking | Hypothesis H1 (to validate) |

**Illustrative sizing for Acme India.** All inputs are **assumptions** to be replaced after validation.

| Input | Assumed value | Note |
|---|---|---|
| Annual T&E spend | ₹30 crore | Assumption |
| Claims per year | 36,000 | Assumption (~3,000/month) |
| Leakage on unaudited spend | 2% | Low end of a vendor's 2–5% savings claim [S5]. Treat as optimistic until validated. |
| Audit coverage today | 15% | Midpoint of the 10–20% vendor figure [S5] |
| Error / rework rate | 19%, 18 min per fix | GBTA ratios [S2] |

- Unaudited spend ≈ ₹30 cr × 85% = **₹25.5 cr**. At 2% leakage, that is **≈ ₹51 lakh/year** at risk.
- Rework ≈ 36,000 × 19% × 18 min ≈ **2,050 hours/year** of employee and finance time.

> **PM note:** This sizing exists to show the *shape* of the value, not to be quoted. An interviewer will ask "where does 2% come from?", and the honest answer is "a vendor claim I have not validated". Say that openly.

### 1.5 Value generated

| Stakeholder | Value | How we'd measure it (see §4) |
|---|---|---|
| CFO / Finance Controller (buyer) | 100% audit coverage without adding headcount; lower leakage; audit-ready trail | Coverage %, $ flagged and confirmed, cost per audited claim |
| Finance auditor (primary user) | Reviews only escalated, high-risk claims, with evidence and policy citations pre-assembled | Claims reviewed per hour, % of time on high-risk claims, override rate |
| Approving manager | Knows a claim is policy-checked before approving, so fewer blind approvals | Time-to-approve, approvals later reversed |
| Employee (claimant) | Faster reimbursement for clean claims; clear reason and fix for rejected ones | Submission-to-reimbursement time, resubmission rate |
| Tax / compliance | Correct GST ITC classification; DPDP-aligned handling of receipt data | ITC-eligible invoices correctly tagged, PII incidents (target 0) |

---

## 2. Users

### 2.1 Who is the primary user, and why

| Role | Type | Why |
|---|---|---|
| **Finance T&E auditor** | **Primary user** | Works with the agent's output daily. They are the human in the loop and decide on escalated claims. The trust design centres on them. |
| Approving manager | Secondary user | Sees the agent's risk signal at approval time; low time investment per claim |
| Employee claimant | Affected user | Rarely sees the agent directly but feels its decisions (speed, rejections) |
| CFO / Finance Controller | Economic buyer | Signs off on budget; cares about leakage, coverage, audit readiness |

> **PM note:** Choosing the auditor as primary is a deliberate call. Most expense apps optimise for the claimant (easy submission). This product's value sits in the *control* function, so the auditor's workflow drives the design.

### 2.2 Personas

> These are **proto-personas**: built from secondary research and assumptions, not interviews. They must be validated (see §5).

**Persona 1: Priya, Finance T&E Auditor (Primary)**

| Attribute | Detail |
|---|---|
| Demographics | 27–35, B.Com/M.Com or CA Inter, 4–8 yrs in AP/T&E, Bengaluru/Pune shared-services team |
| Role | Audits T&E claims after manager approval; handles exceptions; supports GST ITC reconciliation and internal audit |
| Behaviours | Works a queue in the expense tool plus Excel; spot-checks by rules of thumb (round amounts, weekend claims, repeat vendors); emails employees for missing documents |
| Goals | Clear the queue within SLA; catch real violations; stay clean at internal/statutory audit |
| Needs | See *why* a claim is risky, with the exact policy clause and evidence side by side; confidence that auto-cleared claims are actually clean |
| Pains | Volume forces sampling; can't tell a fake receipt by eye; policy ambiguity (is a team dinner "entertainment"?); chasing employees |
| Fears about AI | Being blamed for an AI miss; black-box flags she can't justify to an employee or auditor |
| Success looks like | "I only look at claims that need me, and every flag comes with a reason I can defend." |

**Persona 2: Rahul, Approving Manager (Secondary)**

| Attribute | Detail |
|---|---|
| Demographics | 32–45, engineering or delivery manager, 8–15 direct reports, travels 1–2×/month |
| Behaviours | Approves claims in batches on mobile between meetings; rarely opens receipts |
| Goals | Keep his team happy (fast reimbursement); avoid being questioned about approvals |
| Needs | A one-glance risk signal: "clean" or "check this line, here's why" |
| Pains | Approval is a formality he knows is weak; gets awkward follow-ups from finance after approving |
| Success looks like | "Approve clean claims in one tap; the system tells me when to look." |

**Persona 3: Ananya, Frequent-Travel Employee (Affected)**

| Attribute | Detail |
|---|---|
| Demographics | 25–35, consultant/sales/delivery role, travels 4–8 days/month across Indian metros and Tier-2 cities |
| Behaviours | Pays by corporate card, personal UPI or cash; photographs receipts late; submits in bulk at month-end |
| Goals | Get reimbursed quickly and fully, with minimum admin |
| Needs | Instant feedback on what's wrong *before* submission (missing GSTIN, over limit) |
| Pains | Out-of-pocket spend; rejections without clear reasons; small vendors (autos, local eateries) don't issue proper invoices |
| Success looks like | "If my claim is clean, I get paid without anyone touching it. If not, I know exactly what to fix." |

### 2.3 End-to-end user journey (claim lifecycle, today's state)

| Stage | Who | Actions | Thoughts | Needs | Pain today | Agent opportunity |
|---|---|---|---|---|---|---|
| 1. Spend | Ananya | Books travel, pays hotel/meals/cabs by card, UPI or cash | "Will this be covered?" | Know the policy limits at point of spend | Policy is a long PDF; limits vary by city tier and grade | Out of MVP scope (pre-spend guidance) |
| 2. Capture | Ananya | Photographs receipts, asks hotel for GST invoice | "I'll do it later." | Easy capture; know which documents are required | Lost receipts; invoice lacks company GSTIN | Extract fields and flag missing GSTIN at capture |
| 3. Submit | Ananya | Fills claim, attaches receipts, picks categories | "Please don't bounce this back." | Pre-submission check | Miscategorisation; ~1 in 5 reports has errors [S2] | Pre-check against policy with a cited reason |
| 4. Approve | Rahul | Skims and approves in a batch | "I trust my team; no time to check receipts." | A risk signal at a glance | Blind approval; no evidence surfaced | Risk tier + one-line reason per claim |
| 5. Audit | Priya | Samples claims, checks receipts vs policy, flags exceptions | "I can't check everything. Which ones matter?" | Prioritised queue; evidence + clause side by side | 10–20% coverage [S5]; fakes are hard to spot by eye [S3] | **Core:** 100% automated check; auto-clear low risk; escalate high risk with evidence (HITL) |
| 6. Resolve exceptions | Priya ↔ Ananya | Emails for clarification; partial rejections | "Why is this taking so long?" / "I need a defensible reason." | A clear, specific reason and fix | Back-and-forth; vague reasons | Draft rejection reason with policy citation for Priya to edit and send |
| 7. Reimburse | Finance ops | Payout batch | "When will I get paid?" | Predictable timelines | Clean claims wait behind the audit queue | Clean claims flow straight through (speed as a by-product) |
| 8. Post-audit & tax | Priya / Tax team | GST ITC tagging, internal audit, reporting | "Is our trail audit-ready?" | Complete audit log; correct ITC classification | Manual reconstruction of decisions | Immutable audit trail of every agent and human decision; ITC eligibility tag |

**Moment of truth:** Stage 5 → 6. If Priya cannot understand or defend an agent flag, she will ignore the agent, and the product fails regardless of model accuracy. This is why **explainability with policy citations** is a core requirement, not a nice-to-have.

**MVP focus (proposed, confirmed in later steps):** Stages 3–6 (pre-check, risk signal, audit, exception resolution) + Stage 8 audit trail.

---

## 3. Autonomy policy

> Status: **Approved** (D1–D6, 2026-09-23). Decision records: `docs/DECISIONS.md` ADR-001 to ADR-006.

### 3.1 Principle

How much the agent may do on its own is a **design decision, separate from model capability** [S12]. For every agent action we ask two questions: *what happens if the agent is wrong?* and *can the decision be checked objectively?*

**Core asymmetry:** a wrong approval leaks money, which post-audit can recover. A wrong rejection or fraud accusation harms an employee and trust, which is hard to undo. **The agent may say yes on its own; it may never say no on its own.**

### 3.2 Autonomy matrix

| | Objective check (rules/code decide) | Judgement call (needs interpretation) |
|---|---|---|
| **Low harm / reversible** | Fully automatic | Automatic + random human post-audit |
| **High harm / hard to reverse** | Agent flags, human confirms | Human decides; agent assists |

### 3.3 Action policy

| # | Action | Autonomy | Rationale |
|---|---|---|---|
| A1 | Extract receipt fields, assign category | Automatic; low-confidence fields sent to the employee to confirm | Low harm; schema-validated |
| A2 | Hard-rule checks (limits, exact duplicates, cash > ₹10,000 per person per day [S13]) | Automatic, deterministic code, **no LLM** | Rules are objective; an LLM adds cost and risk |
| A3 | Return to employee for objective, fixable gaps (missing receipt, no company GSTIN, wrong category) | Automatic with a cited reason; if the employee contests, a human decides | Reversible; costs only a short delay |
| A4 | Auto-approve claim | Automatic only if all gates in §3.4 pass, plus random post-audit | Clean claims are the bulk of volume |
| A5 | Partial approval (reimburse up to the cap) | Agent recommends, human decides (MVP) | Affects employee money; candidate for later autonomy once evals support it |
| A6 | Reject claim | **Never automated** | High harm; human keeps final control [S17] |
| A7 | Anomaly (suspected AI-generated or altered receipt, cross-employee duplicate) | Flag labelled "anomaly", never "fraud"; **visible to the auditor only, not the manager** | Protects employees from unfair accusation; the flag is sensitive personal data [S9] |
| A8 | Ambiguous policy interpretation | Agent recommends with policy citations, human decides | Judgement call where errors are costly |
| A9 | GST ITC eligibility tag | Automatic tag; tax team reviews in batches | Reversible before return filing |
| A10 | Policy exceptions (pre-approved overage) | Human only | A business decision, not a policy check |
| A11 | Payment execution | **Out of scope; the agent has no payment tool permission** | Least privilege |

### 3.4 Auto-approve gates (all must pass)

| Gate | Rule | Note |
|---|---|---|
| G1 | All hard rules pass (A2) | — |
| G2 | Extraction is schema-valid and all required fields are present | — |
| G3 | No anomaly signals, **at any amount** | AI-generated fakes average ~$100, apparently pitched below auto-approval thresholds [S3]. An amount cap alone is insufficient. |
| G4 | Confidence from consistency checks, **not the model's self-reported confidence** | LLMs overstate their confidence when asked; agreement across repeated samples helps [S14] |
| G5 | Claim amount ≤ **₹5,000** materiality cap | Starting assumption; tuned in Phase 4 evals |
| G6 | Not selected for the **5%** random post-audit sample | The sample also produces a steady stream of labelled examples for evals |

### 3.5 Guardrails

| Risk | Guardrail |
|---|---|
| Reviewers rubber-stamp the agent (automation bias affects experts and isn't fixed by training [S15]) | Evidence and policy clause shown side by side; reviewer must pick a reason code; track override rate and time per review |
| Agent behaviour drifts | Circuit breaker: if the auto-approve rate leaves its expected band, or a daily ₹ auto-approval limit is hit, everything falls back to recommend-only |
| New model, prompt or policy version | Shadow mode (suggestions logged, not acted on) before it is allowed to act |

### 3.6 Rollout ladder

Shadow mode (the agent suggests, humans decide, outcomes are compared) → Assisted (the agent recommends in the reviewer UI) → Automatic for low-risk claims only (A4 gates). Autonomy is earned with eval evidence at each step. This fits India's AI Governance Guidelines: *People First*, *Accountability*, *Understandable by Design* [S16].

---

## 4. Success metrics

> Status: **Approved** (M1–M6, 2026-09-23). Decision record: `docs/DECISIONS.md` ADR-007. All targets not tied to a source are assumptions, to be revisited after the Phase 4 baseline run.

### 4.1 Measurement principles

- **Offline vs online.** Offline metrics are measured in this project on a labelled golden set of synthetic claims. Online metrics exist only in a real pilot. **The portfolio quotes offline numbers only.**
- **Every metric must drive a decision or block a release.** Q1–Q9 block releases through an automated eval check; H1–H5 trigger ADR revisits.
- **Human review time, not token cost, is the dominant unit cost.** At current Anthropic prices [S17] (Haiku 4.5 $1/$5, Sonnet 5 $2/$10 per 1M input/output tokens), LLM cost is roughly ₹0.5–1.5 per claim (assuming Haiku extraction on every receipt, Sonnet ×3 only on the ~15% of claims needing judgement, ₹88/USD). A human review costs ~₹30 per escalated claim (assuming ~3 min at ₹600/hour loaded). The escalation rate is the main economic lever.

### 4.2 North Star (online)

**Verified audit coverage:** the share of claim value (₹) that is checked against policy *and* whose decision is confirmed correct, by human review or random post-audit. It combines coverage with correctness, so approving everything cannot game it. Baseline ~10–20% [S5]; pilot target ≥95%.

### 4.3 Offline quality gates (block release)

| # | Metric | Target | Rationale |
|---|---|---|---|
| Q1 | False auto-approve rate: auto-approved claims that actually violate policy | ≤1% | Top guardrail. With 0 errors in n cases, the 95% upper bound is ~3/n [S18], so ≥300 claims must be auto-approved (~400 clean, under-cap claims; see `docs/EVAL_PLAN.md`). |
| Q2 | Hard-rule violation recall | 100% | Deterministic code; any miss is a bug |
| Q3 | Recall on interpretation violations (escalated to a human) | ≥85% | Assumption |
| Q4 | Escalation precision (human agrees there is a real issue) | ≥60% | Excess false alerts desensitise reviewers to all alerts [S19] |
| Q5 | Key-field extraction accuracy (amount, date, vendor, GSTIN exact match) | ≥95% | Everything downstream depends on it |
| Q6 | Citation faithfulness (cited clause supports the reason) | ≥95%; LLM judge must agree ≥85% with human labels | Faithfulness evaluation per RAGAS [S20] |
| Q7 | Schema-valid output | 100% after ≤2 retries; ≥95% first pass | Data reliability |
| Q8 | Anomaly (fake receipt) detection recall | Baseline only, no target | Realistic fakes cannot be generated credibly enough to set a target |
| Q9 | Prompt injection via receipt content | 0 successful auto-approvals on the red-team set | OWASP LLM01 [S21] |

### 4.4 Unit economics (offline)

| # | Metric | Target |
|---|---|---|
| E1 | Clean claims cleared with no human involvement | ≥80% |
| E2 | LLM cost per claim | ≤₹1.00 average; routing ≥30% cheaper than an all-Sonnet baseline, with Q1–Q6 within 1 percentage point. **Status: missed at the extraction stage** (Sonnet extraction ≈ ₹1.44/receipt ≈ ₹2.3/claim, ADR-017); target revisited in Phase 5. |
| E3 | Total cost per claim (LLM + human minutes × assumed rate) | Reported against an all-human-review baseline |
| E4 | p95 latency per claim | ≤20 seconds |

### 4.5 Human-review health (online; simulated in the demo)

| # | Metric | Target / band | Links to |
|---|---|---|---|
| H1 | Reviewer override rate | 5–30% | §3.5 automation-bias guardrail |
| H2 | Median review time | Alert if under 10 seconds | §3.5 |
| H3 | Employee contest rate on automatic returns | ≤10% | ADR-002 |
| H4 | Auto-approve rate drift | ±10 percentage points vs shadow baseline, otherwise fallback to recommend-only | ADR-006, §3.5 |
| H5 | Partial-approval agreement with humans | ≥95% over ≥100 cases | ADR-005 |

---

## 5. Evidence gaps & validation plan

### Hypotheses to validate

| ID | Hypothesis | Risk if wrong |
|---|---|---|
| H1 | Indian mid-size finance teams audit a sample (not 100%) of T&E claims | Core premise fails; pivot to a speed or GST angle |
| H2 | Auditors would accept auto-clearance of low-risk claims if every decision is logged and explainable | HITL design must change (e.g., agent only recommends) |
| H3 | Clean claims wait meaningfully because of the audit queue | Employee value proposition weakens |
| H4 | Missing or incorrect GST invoice details cause material lost ITC on T&E | Drop the GST feature from MVP |
| H5 | Fake or altered receipts are a real concern for Indian finance teams, not just US/UK | "Why now" argument weakens for India |

### Validation plan (lean, 1 week)

- 5 short conversations (20 min each): 2 finance/AP or T&E auditors, 1 finance controller, 1 people manager, 1 frequent traveller.
- Core questions:
  1. "Walk me through the last claim you rejected. What made you look at it?"
  2. "What % of claims do you actually open and check?"
  3. "If a system cleared low-risk claims automatically, what would you need to see to trust it?"
  4. "How much time do you spend on GST invoice issues in T&E?"
  5. "Have you seen a receipt you suspected was fake or edited?"
- Update the personas, sizing and hypotheses table with what you learn. Record findings in `docs/DECISIONS.md`.

> **PM note:** A portfolio PRD that says "I ran 5 interviews and they changed X" is worth far more than one with perfect secondary research. If time is short, even 2–3 conversations with finance contacts will do.

---

## 6. Sources

| ID | Source | URL |
|---|---|---|
| S1 | ACFE, *Occupational Fraud 2024: A Report to the Nations* (figures verified via a public copy of the PDF) | https://www.acfe.com/-/media/files/acfe/pdfs/rttn/2024/2024-report-to-the-nations.pdf · public copy: https://www.anchin.com/wp-content/uploads/2024/08/2024-ACFE-Occupational-Fraud-Report.pdf |
| S2 | GBTA Foundation, *How Much Do Expense Reports Really Cost a Company?* (Oct 2015) | https://gbta.org/how-much-do-expense-reports-really-cost-a-company/ |
| S3 | PYMNTS, *AI-Generated Fake Receipts Now Make Up 71% of Expense Fraud* (AppZen data, 2026) | https://www.pymnts.com/news/artificial-intelligence/2026/ai-generated-fake-receipts-now-make-up-71percent-of-expense-fraud/ |
| S4 | Accounting Today, *Use of AI receipts in expense fraud soars* (AppZen + Emburse survey) | https://www.accountingtoday.com/news/use-of-ai-receipts-in-expense-fraud-soars |
| S5 | AppZen, *AI Makes 100% Prepayment Expense Audits Affordable* (vendor content) | https://www.appzen.com/blog/100-percent |
| S6 | Gartner, *Finance AI Adoption Remains Steady in 2025* (18 Nov 2025) | https://www.gartner.com/en/newsroom/press-releases/2025-11-18-gartner-survey-shows-finance-ai-adoption-remains-steady-in-2025 |
| S7 | DEV Community, *Inscribe says AI is under 5% of document fraud, AppZen 70.8%. Both are right.* | https://dev.to/haruodev/inscribe-says-ai-is-under-5-of-document-fraud-appzen-708-both-are-right-3cg3 |
| S8 | a16z, *Welcome to LLMflation* (Nov 2024) | https://a16z.com/llmflation-llm-inference-cost/ |
| S9 | S&R Associates, *India's Digital Personal Data Protection Regime Takes Effect* | https://www.snrlaw.in/indias-digital-personal-data-protection-regime-takes-effect/ |
| S10 | ClearTax, *Section 17(5) of CGST Act — Blocked Credit* | https://cleartax.in/s/section-175-of-cgst-act |
| S11 | GSTZen, *How ITC is Treated on Hotel Stays for Business Travel* | https://gstzen.in/a/how-itc-treated-on-hotel-stays-for-business-travel.html |
| S12 | Feng, McDonald & Zhang, *Levels of Autonomy for AI Agents* (2025) | https://arxiv.org/abs/2506.12469 |
| S13 | ClearTax, *Section 40A(3) of Income Tax Act* | https://cleartax.in/s/section-40a3-of-income-tax-act |
| S14 | Xiong et al., *Can LLMs Express Their Uncertainty?* (2023) | https://arxiv.org/abs/2306.13063 |
| S15 | Parasuraman & Manzey, *Complacency and Bias in Human Use of Automation* (Human Factors, 2010) | https://journals.sagepub.com/doi/10.1177/0018720810376055 |
| S16 | MeitY, *India AI Governance Guidelines* (Nov 2025) | https://static.pib.gov.in/WriteReadData/specificdocs/documents/2025/nov/doc2025115685601.pdf |
| S17 | Anthropic, *Models overview & pricing* (accessed 2026-09-26; replaces Gemini pricing per ADR-013) | https://platform.claude.com/docs/en/models/overview |
| S18 | Statology, *A Concise Guide to the Statistical Rule of Three* | https://www.statology.org/a-concise-guide-to-the-statistical-rule-of-three/ |
| S19 | AHRQ PSNet, *Alert Fatigue* (primer) | https://psnet.ahrq.gov/primer/alert-fatigue |
| S20 | Es et al., *RAGAS: Automated Evaluation of Retrieval Augmented Generation* (2023) | https://arxiv.org/abs/2309.15217 |
| S21 | OWASP GenAI Security Project, *LLM01:2025 Prompt Injection* | https://genai.owasp.org/llmrisk/llm01-prompt-injection/ |
