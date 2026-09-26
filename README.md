# Expense Audit Agent

> 🚧 Work in progress. Built in public, docs-first: the problem, autonomy policy, metrics and eval plan were written before any agent code.

An agentic AI system that audits employee travel & expense claims for a (fictional) Indian company. It checks every claim against policy, auto-approves only low-risk claims, and escalates the rest to a human auditor with evidence and policy citations.

It demonstrates three operational challenges of AI products:

- **Data reliability:** schema-validated extraction, policy RAG with clause-level citations
- **Autonomy & human oversight:** explicit autonomy policy, human-in-the-loop review, audit trail
- **Unit economics & trust:** evals as release gates, cost/latency tracking, model routing

## Read the product thinking first

| Doc | What's in it |
|---|---|
| [PRD](docs/PRD.md) | Problem, users, journey, autonomy policy, success metrics |
| [Architecture](docs/ARCHITECTURE.md) | Claim flow, components, why the LLM never makes the final decision |
| [Eval plan](docs/EVAL_PLAN.md) | Golden set, gates, baselines, CI |
| [Decision log](docs/DECISIONS.md) | Every major decision, with rejected alternatives |
| [Policy](policy/POLICY.md) | The synthetic company T&E policy (generated from `policy/limits.yaml`) |

All company data in this repo is synthetic. Generated receipts are watermarked "SYNTHETIC SAMPLE — NOT A VALID INVOICE".
