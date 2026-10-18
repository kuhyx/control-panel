"""Percentiles and histogram buckets, shared by the context and latency panels.

Percentiles are nearest-rank (the smallest value with at least ``q`` of the
values at or below it): always a value that was really observed.
"""

from __future__ import annotations

from bisect import bisect_right
import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence


def percentile(values: Sequence[float], q: float) -> float | None:
    """Nearest-rank ``q`` quantile (0 < q <= 1), ``None`` for no values."""
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(q * len(ordered)) - 1)]


def percentiles(
    values: Sequence[float], qs: Sequence[float]
) -> dict[str, float | None]:
    """``{"p50": ..., "p90": ...}`` for each quantile in ``qs``."""
    ordered = sorted(values)
    return {f"p{round(q * 100)}": percentile(ordered, q) for q in qs}


def bucket(value: float, edges: Sequence[float]) -> int:
    """Index of the bucket ``value`` falls in: ``[edges[i], edges[i+1])``."""
    return max(0, bisect_right(edges, value) - 1)
