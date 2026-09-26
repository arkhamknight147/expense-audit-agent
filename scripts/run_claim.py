"""Run ONE claim end to end and act as the auditor in the terminal (T3.5, D6).

Usage:
  python scripts/run_claim.py C0123                 # run (or resume if paused) claim C0123
  python scripts/run_claim.py C0123 --mode shadow   # shadow | assisted | auto (default from .env)
  python scripts/run_claim.py C0123 --log           # show the claim's audit trail + chain check
  python scripts/run_claim.py C0123 --fresh         # start a new run even if one exists

Uses the Anthropic API for extraction and interpretation (cached results are reused, so
dev claims already evaluated cost nothing). Reads claims and the ledger only; never labels.
"""
import argparse
import json
import sys
import textwrap
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from expense_audit import store  # noqa: E402
from expense_audit.config import AUTONOMY_MODE, DB_PATH, GOLDEN_DIR  # noqa: E402

CHECKPOINTS = ROOT / "data" / "checkpoints.db"


def load_claim(cid: str) -> dict:
    for line in open(GOLDEN_DIR / "claims.jsonl", encoding="utf-8"):
        c = json.loads(line)
        if c["claim_id"] == cid:
            return c
    raise SystemExit(f"Claim {cid} not found in evals/golden/claims.jsonl")


def show_packet(p: dict, claim: dict) -> None:
    print("\n" + "=" * 72)
    print(f"REVIEW NEEDED  {p['claim_id']}   total Rs {p['claim_total']:,.2f}")
    print("=" * 72)
    for li in claim["line_items"]:
        print(f"  {li['line_id']}  {li['category']:<22} Rs {li['amount_claimed']:>10,.2f}  receipt: {li.get('receipt') or '(none)'}")
    print(f"\nAgent recommendation: {p['agent_recommendation']}")
    for r in p["reasons"]:
        print(f"  - {r}")
    if p["anomalies"]:
        print("\nAnomalies (auditor-only):")
        for a in p["anomalies"]:
            print(f"  ! {a['type']} {a.get('line_id') or ''}: {a['evidence']}")
    for i in p["interpretations"]:
        print(f"\nInterpretation {i['clause_id']}: {i['verdict']} ({i['agreement']})")
        print(textwrap.indent(textwrap.fill(i["rationale"], 68), "  "))
        if i.get("ask_employee"):
            print(f"  Ask the employee: {i['ask_employee']}")
    for cid, text in p["clauses"].items():
        print(f"\n[{cid}] " + textwrap.shorten(text.replace("\n", " "), 300))
    print()


def ask_review(packet: dict, input_fn=input) -> dict:
    actions = list(packet["allowed_actions"])
    for n, a in enumerate(actions, 1):
        print(f"  {n}. {a}")
    action = actions[int(input_fn("Action number: ").strip()) - 1]
    reasons = packet["allowed_actions"][action]
    for n, r in enumerate(reasons, 1):
        print(f"  {n}. {r}")
    review = {"action": action, "reason_code": reasons[int(input_fn("Reason number: ").strip()) - 1],
              "reviewer": input_fn("Your reviewer ID: ").strip()}
    if action == "partial_approve":
        review["approved_amount"] = float(input_fn("Approved amount (Rs): ").strip())
    note = input_fn("Note (optional): ").strip()
    if note:
        review["note"] = note
    return review


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("claim_id")
    ap.add_argument("--mode", choices=["shadow", "assisted", "auto"], default=AUTONOMY_MODE)
    ap.add_argument("--log", action="store_true")
    ap.add_argument("--fresh", action="store_true")
    a = ap.parse_args()

    db = store.connect(DB_PATH)
    if a.log:
        for e in store.events(db, a.claim_id):
            print(f"{e['id']:>4} {e['ts']} {e['actor']:<16} {e['action']:<28} {e['reason_code'] or ''}")
        ok, bad = store.verify_chain(db)
        print(f"\nAudit chain intact: {ok}" + ("" if ok else f" (first bad row {bad})"))
        return 0

    import anthropic
    from langgraph.types import Command

    from expense_audit.extract import extract_receipt
    from expense_audit.graph import build_graph, sqlite_checkpointer, validate_review

    client = anthropic.Anthropic(max_retries=5)
    graph = build_graph(extract_fn=lambda p: extract_receipt(p, client=client), interpret_client=client, db=db,
                        checkpointer=sqlite_checkpointer(str(CHECKPOINTS)), mode=a.mode)
    thread = a.claim_id if not a.fresh else f"{a.claim_id}-{uuid.uuid4().hex[:6]}"
    cfg = {"configurable": {"thread_id": thread}}
    claim = load_claim(a.claim_id)
    state = graph.get_state(cfg)

    if state.next == ("human_review",):
        print(f"Resuming paused review for {a.claim_id} ...")
        packet = state.tasks[0].interrupts[0].value
    elif state.values.get("final_status"):
        print(f"{a.claim_id} already finished: {state.values['final_status']} (use --fresh to re-run, --log for the trail)")
        return 0
    else:
        print(f"Running {a.claim_id} in '{a.mode}' mode ...")
        out = graph.invoke({"claim": claim, "ledger": [json.loads(l) for l in open(GOLDEN_DIR / "ledger.jsonl", encoding="utf-8")]}, cfg)
        if "__interrupt__" not in out:
            d = out["decision"]
            print(f"\nDecision: {out['final_status']}")
            for r in d["reasons"]:
                print(f"  - {r}")
            print(f"ITC tags: {d['itc_tags']}")
            return 0
        packet = out["__interrupt__"][0].value

    show_packet(packet, claim)
    while True:
        try:
            review = validate_review(ask_review(packet), packet["claim_total"])
            break
        except (ValueError, IndexError) as exc:
            print(f"  Invalid input: {exc}. Try again.\n")
    out = graph.invoke(Command(resume=review), cfg)
    print(f"\nFinal status: {out['final_status']}  (audit trail: python scripts/run_claim.py {a.claim_id} --log)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
