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

EXTRACT_MODEL = os.getenv("EXTRACT_MODEL", "gemini-flash-lite-latest")
INTERPRET_MODEL = os.getenv("INTERPRET_MODEL", "gemini-flash-latest")
JUDGE_MODEL = os.getenv("JUDGE_MODEL", "openai/gpt-oss-120b")
INTERPRET_SAMPLES = int(os.getenv("INTERPRET_SAMPLES", "3"))
