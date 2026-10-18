"""Hard harness limits and soft budgets for context files.

Both live in ``context_limits.json`` next to this module (edit it to change
a budget). A file's status is ``over hard limit`` when it breaks a verified
harness limit (the part past it is not loaded, or the file is skipped),
``over budget`` when it only breaks one of kuhy's soft budgets, else ``ok``.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

CONFIG = Path(__file__).with_name("context_limits.json")
MEASURES = (
    ("lines", "lines"),
    ("bytes", "bytes"),
    ("standing_bytes", "standing bytes"),
    ("tokens", "tokens"),
)
OK, OVER_BUDGET, OVER_HARD = "ok", "over budget", "over hard limit"


@dataclass(frozen=True)
class Size:
    """What one context file measures."""

    name: str
    kind: str
    standing: str
    lines: int
    bytes: int
    standing_bytes: int
    tokens: int


def load(path: Path = CONFIG) -> dict[str, Any]:
    """The limits config."""
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return data


def _applies(rule: dict[str, Any], size: Size) -> bool:
    """Whether every selector the rule gives matches the file."""
    return (
        rule.get("name", size.name) == size.name
        and str(rule.get("kind", "")) in size.kind
        and rule.get("standing", size.standing) == size.standing
    )


def _breaches(rules: list[dict[str, Any]], size: Size) -> list[dict[str, Any]]:
    """Every (rule, measure) the file is over, with the numbers."""
    out = []
    for rule in rules:
        if not _applies(rule, size):
            continue
        for key, label in MEASURES:
            limit = rule.get(key)
            value = getattr(size, key)
            if limit is not None and value > limit:
                out.append(
                    {
                        "measure": label,
                        "value": value,
                        "limit": limit,
                        "why": rule["why"],
                    }
                )
    return out


def _limits(rules: list[dict[str, Any]], size: Size) -> list[str]:
    """Every limit that applies, as text (``25,000 bytes``)."""
    return [
        f"{rule[key]:,} {label}"
        for rule in rules
        if _applies(rule, size)
        for key, label in MEASURES
        if key in rule
    ]


def status(config: dict[str, Any], size: Size) -> dict[str, Any]:
    """Status, the breaches behind it, and the limits that apply."""
    hard = _breaches(config["hard"], size)
    soft = _breaches(config["budgets"], size)
    return {
        "status": OVER_HARD if hard else OVER_BUDGET if soft else OK,
        "breaches": [{**b, "hard": True} for b in hard]
        + [{**b, "hard": False} for b in soft],
        "hard_limits": _limits(config["hard"], size),
        "budgets": _limits(config["budgets"], size),
    }
