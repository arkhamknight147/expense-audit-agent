"""Policy access: limits from limits.yaml (single source of truth) and clause text by ID."""
from __future__ import annotations

import re
from functools import lru_cache

import yaml

from .config import LIMITS_PATH, POLICY_PATH

_CLAUSE_RE = re.compile(r"^### ([A-Z]+-\d{2}) — (.+)$", re.M)


@lru_cache(maxsize=1)
def config() -> dict:
    return yaml.safe_load(LIMITS_PATH.read_text(encoding="utf-8"))


def limits() -> dict:
    return config()["limits"]


def city_tier(city: str) -> str:
    tiers = config()["city_tiers"]
    if city in tiers["X"]:
        return "X"
    if city in tiers["Y"]:
        return "Y"
    return "Z"


def hotel_limit(grade: str, city: str) -> int:
    return limits()["hotel_per_night"][grade][city_tier(city)]


def meal_limit(grade: str) -> int:
    return limits()["meals_per_day"][grade]


def transport_limit(grade: str) -> int | None:
    return limits()["local_transport_per_day"][grade]


def clause_registry() -> list[dict]:
    return config()["clauses"]


@lru_cache(maxsize=1)
def clause_texts() -> dict[str, str]:
    """Map clause ID -> exact clause text from the generated POLICY.md (used for citations)."""
    text = POLICY_PATH.read_text(encoding="utf-8")
    matches = list(_CLAUSE_RE.finditer(text))
    out = {}
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[m.end():end]
        body = re.split(r"^## ", body, flags=re.M)[0]  # stop at next section heading
        out[m.group(1)] = f"{m.group(1)} — {m.group(2)}\n{body.strip()}"
    return out


def clause_text(clause_id: str) -> str:
    return clause_texts()[clause_id]
