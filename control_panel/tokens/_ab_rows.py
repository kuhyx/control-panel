"""The A/B comparison as table rows (one per measure), for DataTable and API.

Cells are display strings (a mean or rate with its 95% interval), so the
table layer searches and sorts them as text; the raw numbers stay in
``arms`` / ``diffs`` of the same payload.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

ARMS = ("sonnet", "opus")
MINUTE = 60
HOUR = 3600
RATES = (
    ("redo", "redo rate (similar Agent re-dispatched)"),
    ("followup", "follow-up rate (SendMessage after return)"),
    ("error", "error / aborted rate"),
    ("correction", "user-correction rate (noisy: phrase match)"),
)


def _share(value: float) -> str:
    """0.123 -> 12.3%."""
    return f"{value * 100:.1f}%"


def _usd(value: float) -> str:
    """Two decimals, like the frontend's formatUsd under $100."""
    return f"${value:.2f}"


def _duration(seconds: float) -> str:
    """42s / 7m / 1h05, like the frontend's formatDuration."""
    if seconds < MINUTE:
        return f"{round(seconds)}s"
    if seconds < HOUR:
        return f"{round(seconds / MINUTE)}m"
    minutes = round(seconds / MINUTE)
    return f"{minutes // MINUTE}h{minutes % MINUTE:02d}"


def _rate(cell: dict[str, Any] | None) -> str:
    """A rate with its Wilson interval, or a dash when there is none."""
    if not cell or cell.get("rate") is None:
        return "—"
    return f"{_share(cell['rate'])} [{_share(cell['low'])}, {_share(cell['high'])}]"


def _per_arm(
    arms: dict[str, Any], render: Callable[[dict[str, Any]], str]
) -> dict[str, str]:
    """``render`` applied to each present arm; a dash for a missing one."""
    return {name: _safe(render, arms.get(name)) for name in ARMS}


def _safe(render: Callable[[dict[str, Any]], str], arm: dict[str, Any] | None) -> str:
    """``render(arm)``, or a dash when the arm (or a field of it) is missing."""
    try:
        return "—" if arm is None else render(arm)
    except KeyError:
        return "—"


def rows(payload: dict[str, Any]) -> list[dict[str, str]]:
    """Every measure as ``{measure, sonnet, opus, difference}``."""
    arms: dict[str, Any] = payload.get("arms") or {}
    diffs: dict[str, Any] = payload.get("diffs") or {}
    out = [
        {"measure": "n", **{n: str(arms.get(n, {}).get("n", 0)) for n in ARMS}},
        {
            "measure": "cost per agent (mean, 95% CI)",
            **_per_arm(
                arms,
                lambda a: (
                    f"{_usd(a['usd']['mean'])} [{_usd(a['usd']['low'])},"
                    f" {_usd(a['usd']['high'])}]"
                ),
            ),
        },
        {
            "measure": "duration (mean)",
            **_per_arm(arms, lambda a: _duration(a["duration_s"]["mean"])),
        },
    ]
    for key, label in RATES:
        diff = diffs.get(key)
        out.append(
            {
                "measure": label,
                **{n: _rate(arms.get(n, {}).get(key)) for n in ARMS},
                "difference": "—"
                if diff is None
                else f"{_share(diff['diff'])} [{_share(diff['low'])},"
                f" {_share(diff['high'])}]",
            }
        )
    out.append(
        {
            "measure": "parent session end tag",
            **_per_arm(
                arms, lambda a: ", ".join(f"{t} {n}" for t, n in a["tags"].items())
            ),
        }
    )
    return [{"difference": "", **row} for row in out]
