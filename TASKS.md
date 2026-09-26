# Tasks

## Current status
- **Phase:** 2 complete → starting Phase 3 (MVP build)
- **Next task:** T3.1 smoke run (PM runs locally) → full dev run → T3.2 Rules engine
- **Known issues:** HTL-03 judgement cases check out on Sunday while some justifications mention Monday (generator artefact, accepted as is). CORD extraction slice not yet added (G8).

## Phase 0 — Framing ✅
- [x] 0.1 Problem & users (PRD §1–2)
- [x] 0.2 Autonomy policy (PRD §3, ADR-001–006)
- [x] 0.3 Success metrics (PRD §4, ADR-007)
- [x] 0.4 Eval plan (EVAL_PLAN, ADR-008)

## Phase 1 — Data ✅
- [x] 1.1 Policy corpus (limits.yaml → POLICY.md, ADR-009)
- [x] 1.2 Golden set: 630 claims, 1,012 receipts (ADR-010)
- [x] 1.2b Judgement labels (ADR-011)
- [ ] 1.2c PM 10% re-label check (due ~2026-10-03)
- [ ] 1.2d CORD extraction slice (~50 receipts)

## Phase 2 — Architecture ✅
- [x] 2.1 ARCHITECTURE.md, ADR-012
- [x] 2.2 Repo scaffold: pyproject, AGENTS.md, TASKS.md, config, policy module + tests

## Phase 3 — MVP (thin end-to-end first)
- [~] T3.1 Extraction (code + 15 unit tests done; awaiting smoke & dev runs): `schemas.py` + `extract.py` (Claude Haiku 4.5, schema, retries, validation log) → Q5, Q7 on dev
- [ ] T3.2 Rules engine: `rules.py`, one function per `check` → Q2 = 100% on dev
- [ ] T3.3 Anomaly checks: `anomaly.py` (GST maths, GSTIN state, ledger duplicates, injection signal)
- [ ] T3.4 Clause lookup + interpretation: `interpret.py` (Claude Sonnet 5 ×3, cited clause IDs)
- [ ] T3.5 Gates + graph: `decide.py`, `graph.py` with `interrupt()`, `store.py` audit log

## Phase 4 — Evals
- [ ] 4.1 Eval harness + baselines B1 (rules-only) and B2 (single strong model)
- [ ] 4.2 LLM judge (Groq) calibrated ≥85% vs PM labels
- [ ] 4.3 GitHub Actions: smoke subset per commit, full test at release

## Phase 5 — Economics & trust
- [ ] 5.1 Routing comparison + Langfuse traces (E1–E4)
- [ ] 5.2 Red-team run (Q9)

## Phase 6 — Ship
- [ ] 6.1 Streamlit auditor UI on Community Cloud
- [ ] 6.2 EVAL_REPORT.md + README + 2-min walkthrough
- [ ] 6.3 Resume bullet, LinkedIn post, interview narrative
