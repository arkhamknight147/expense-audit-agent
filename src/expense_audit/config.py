"""Paths, environment and model configuration."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

POLICY_DIR = ROOT / "policy"
LIMITS_PATH = POLICY_DIR / "limits.yaml"
POLICY_PATH = POLICY_DIR / "POLICY.md"
GOLDEN_DIR = ROOT / "evals" / "golden"
DB_PATH = ROOT / "data" / "expense_audit.db"

AUTO_APPROVE_CAP = 5000          # G5, ADR-004
POST_AUDIT_SAMPLE_RATE = 0.05    # G6, ADR-004

EXTRACT_MODEL = os.getenv("EXTRACT_MODEL", "claude-haiku-4-5-20251001")
INTERPRET_MODEL = os.getenv("INTERPRET_MODEL", "claude-sonnet-5")
JUDGE_MODEL = os.getenv("JUDGE_MODEL", "openai/gpt-oss-120b")
INTERPRET_SAMPLES = int(os.getenv("INTERPRET_SAMPLES", "3"))

# USD per 1M tokens (input, output). Source: https://platform.claude.com/docs/en/models/overview
# (accessed 2026-09-26). Update here if prices change; cost metrics E2/E3 read this table.
PRICES_USD_PER_MTOK = {
    "claude-haiku-4-5-20251001": (1.0, 5.0),
    "claude-sonnet-5": (2.0, 10.0),
}
USD_INR = float(os.getenv("USD_INR", "88"))  # assumption for reporting in INR


def usd_cost(model: str, input_tokens: int, output_tokens: int) -> float | None:
    price = PRICES_USD_PER_MTOK.get(model)
    if price is None:
        return None
    return round(input_tokens / 1e6 * price[0] + output_tokens / 1e6 * price[1], 6)
