"""GSTIN format and checksum (T3.1 fix F1/F2).

A GSTIN is 15 characters: 2-digit state code, 10-character PAN (5 letters, 4 digits,
1 letter), 1 entity code (1-9 or A-Z), the letter 'Z', and a check character computed
with the GSTN mod-36 algorithm below. The checksum lets us detect almost all
single-character misreads (Z/2, O/0, I/1 ...) without knowing the true value.
"""
import re

CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
FORMAT_RE = re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")


def check_char(first14: str) -> str:
    total = 0
    for i, c in enumerate(first14):
        d = CHARS.index(c) * (1 if i % 2 == 0 else 2)
        total += d // 36 + d % 36
    return CHARS[(36 - total % 36) % 36]


def normalise(value: str | None) -> str:
    return re.sub(r"\s", "", value or "").upper()


def is_valid(value: str | None) -> bool:
    g = normalise(value)
    return bool(FORMAT_RE.match(g)) and check_char(g[:14]) == g[14]
