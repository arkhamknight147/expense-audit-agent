"""Block commits that contain API keys or tokens (no dependencies, runs on Windows/macOS/Linux).

Usage:
  python scripts/check_secrets.py --staged   # used by the git pre-commit hook
  python scripts/check_secrets.py --all      # scan every tracked + untracked (non-ignored) file
Exit code 1 = a likely secret was found (commit is blocked).
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PATTERNS = {
    "Anthropic API key": re.compile(r"sk-ant-[A-Za-z0-9_\-]{20,}"),
    "Groq API key": re.compile(r"gsk_[A-Za-z0-9]{20,}"),
    "Google API key": re.compile(r"AIza[0-9A-Za-z_\-]{30,}"),
    "Langfuse secret key": re.compile(r"sk-lf-[A-Za-z0-9\-]{10,}"),
    "OpenAI-style key": re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9]{32,}"),
    "GitHub token": re.compile(r"\b(?:ghp|gho|ghu|ghs)_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}"),
    "Private key block": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "Key assigned in code": re.compile(r"(?i)(api_key|secret_key|token)\s*=\s*['\"][A-Za-z0-9_\-]{24,}['\"]"),
}
FORBIDDEN_FILES = {".env"}
SKIP_SUFFIXES = {".jpg", ".jpeg", ".png", ".gif", ".pdf", ".ico", ".zip"}


def _git(*args: str) -> list[str]:
    out = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    return [l for l in out.splitlines() if l.strip()]


def files_to_scan(mode: str) -> list[str]:
    if mode == "--staged":
        return _git("diff", "--cached", "--name-only", "--diff-filter=ACM")
    return _git("ls-files", "--cached", "--others", "--exclude-standard")


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "--staged"
    findings = []
    for rel in files_to_scan(mode):
        p = ROOT / rel
        if Path(rel).name in FORBIDDEN_FILES or (Path(rel).name.startswith(".env.") and Path(rel).name != ".env.example"):
            findings.append(f"{rel}: secrets file must never be committed")
            continue
        if p.suffix.lower() in SKIP_SUFFIXES or not p.is_file():
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if rel.replace("\\", "/") == "scripts/check_secrets.py":
            continue  # this file contains the patterns themselves
        for n, line in enumerate(text.splitlines(), 1):
            for name, rx in PATTERNS.items():
                if rx.search(line):
                    findings.append(f"{rel}:{n}: possible {name}")
    if findings:
        print("SECRET CHECK FAILED — commit blocked:\n  " + "\n  ".join(findings))
        print("Remove the secret (keep it only in .env), then commit again.")
        return 1
    print(f"Secret check passed ({mode}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
