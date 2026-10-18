"""List prices per token class, for pricing input / writes / reads / output.

The store keeps one ``usd`` per call, not per class, so the token-class and
output panels price each class themselves with the table token_audit used to
compute ``turns.usd`` (``token_classes_prices.json``, a copy of
``testsAndMisc/python_pkg/token_audit/prices.json``). The lookup is
token_audit's: exact id, else the longest known id it starts with, else the
default model. Turns with no 1h/5m split are priced as 5m writes, as there.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

PRICES = Path(__file__).with_name("token_classes_prices.json")
PER_MILLION = 1_000_000


@dataclass(frozen=True)
class Price:
    """USD per million tokens of each class, for one model."""

    input: float
    output: float
    cache_read: float
    write_5m: float
    write_1h: float

    def usd(self, tokens: float, per_mtok: float) -> float:
        """``tokens`` at ``per_mtok`` dollars per million."""
        return tokens * per_mtok / PER_MILLION


@dataclass(frozen=True)
class PriceBook:
    """Every known model's price plus the fallback for unknown ids."""

    models: dict[str, Price]
    default: str
    source: str

    def price(self, model: str) -> Price:
        """Exact id, else the longest known id it starts with, else default."""
        if model in self.models:
            return self.models[model]
        matches = [known for known in self.models if model.startswith(known)]
        return self.models[max(matches, key=len) if matches else self.default]


def load(path: Path = PRICES) -> PriceBook:
    """Read the price table shipped next to this module."""
    data = json.loads(path.read_text(encoding="utf-8"))
    mult = data["cache_write_multipliers"]
    models = {
        name: Price(
            input=float(row["input"]),
            output=float(row["output"]),
            cache_read=float(row["cache_read"]),
            write_5m=float(row["input"]) * float(mult["5m"]),
            write_1h=float(row["input"]) * float(mult["1h"]),
        )
        for name, row in data["models"].items()
    }
    return PriceBook(models, str(data["default"]), str(data["_source"]))


BOOK = load()
