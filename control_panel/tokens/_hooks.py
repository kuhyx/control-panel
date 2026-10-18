"""Hooks: what each hook costs in runtime, injected context and forced retries.

Every number comes from ``marks`` rows of kind ``hook_*`` (the ingester
aggregates them per prompt + kind + hookName + script, so ``count`` is the
number of events and ``duration_ms`` is already summed over them). A hook
costs its *injected context* (``hook_context`` + ``hook_run`` tokens, their
creation and carry -- see :mod:`_carry`) plus, for a block or a Stop bounce,
the *retry* it forced (``retry_usd``: the calls that would not have happened
without it). The budget-gate table (:mod:`_hooks_budget`) is a live snapshot.
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, Any

from control_panel.tokens import _hooks_budget
from control_panel.tokens._registry import panel

if TYPE_CHECKING:
    import sqlite3

    from control_panel.tokens._db import Filters

TOP = 25
STOPS = ("Stop", "SubagentStop")
CAPTION = (
    "Per hook (hookName + script). fires = hook_run events; runtime = their "
    "summed duration as the harness reported it (hooks without a duration "
    "count as 0, so the mean can read low). Injected = hook_context + "
    "hook_run tokens with their creation + carry cost (estimated 4 "
    "chars/token). retry $ = the API calls a block or Stop bounce forced. "
    "Context and errors logged without a script name form their own row."
)

_PER_HOOK = (
    "SELECT name, detail,"
    " SUM(CASE WHEN kind = 'hook_run' THEN count ELSE 0 END),"
    " SUM(CASE WHEN kind = 'hook_run' THEN duration_ms ELSE 0 END),"
    " SUM(CASE WHEN kind IN ('hook_run', 'hook_context') THEN tokens ELSE 0 END),"
    " SUM(CASE WHEN kind IN ('hook_run', 'hook_context') THEN create_usd"
    " ELSE 0 END),"
    " SUM(CASE WHEN kind IN ('hook_run', 'hook_context') THEN carry_usd"
    " ELSE 0 END),"
    " SUM(CASE WHEN kind = 'hook_block' THEN count ELSE 0 END),"
    " SUM(CASE WHEN kind = 'hook_block' THEN retry_usd ELSE 0 END),"
    " SUM(CASE WHEN kind = 'hook_error' THEN count ELSE 0 END),"
    " SUM(CASE WHEN kind = 'hook_msg' THEN count ELSE 0 END)"
    " FROM marks WHERE"
    " ts BETWEEN ? AND ?"
    " AND (? = '' OR cwd = ? OR cwd LIKE ? || '/%')"
    " AND (? = '' OR model = ?)"
    " AND (? = -1 OR is_sub = ?)"
    " AND kind IN ('hook_run', 'hook_context', 'hook_block', 'hook_error',"
    " 'hook_msg') GROUP BY name, detail"
)
_STOPS = (
    "SELECT name, detail, SUM(count), SUM(retry_usd) FROM marks WHERE"
    " ts BETWEEN ? AND ?"
    " AND (? = '' OR cwd = ? OR cwd LIKE ? || '/%')"
    " AND (? = '' OR model = ?)"
    " AND (? = -1 OR is_sub = ?)"
    " AND kind = 'hook_block' AND name IN (?, ?) GROUP BY name, detail"
    " ORDER BY SUM(retry_usd) DESC, SUM(count) DESC"
)
_DAILY = (
    "SELECT day,"
    " SUM(CASE WHEN kind IN ('hook_run', 'hook_context')"
    " THEN create_usd + carry_usd ELSE 0 END),"
    " SUM(CASE WHEN kind = 'hook_block' THEN retry_usd ELSE 0 END)"
    " FROM marks WHERE"
    " ts BETWEEN ? AND ?"
    " AND (? = '' OR cwd = ? OR cwd LIKE ? || '/%')"
    " AND (? = '' OR model = ?)"
    " AND (? = -1 OR is_sub = ?)"
    " AND kind IN ('hook_run', 'hook_context', 'hook_block') GROUP BY day"
    " ORDER BY day"
)
_SPEND = (
    "SELECT COALESCE(SUM(usd), 0) FROM turns WHERE"
    " ts BETWEEN ? AND ?"
    " AND (? = '' OR cwd = ? OR cwd LIKE ? || '/%')"
    " AND (? = '' OR model = ?)"
    " AND (? = -1 OR is_sub = ?)"
)


def _hook(row: tuple[Any, ...]) -> dict[str, Any]:
    """One hook's fires, runtime, injected context, blocks and errors."""
    name, detail, fires, ms, tokens, create, carry, blocks, retry, errors, msgs = row
    create, carry, retry = create or 0.0, carry or 0.0, retry or 0.0
    return {
        "hook": name,
        "script": detail,
        "fires": fires,
        "runtime_s": (ms or 0) / 1000,
        "mean_ms": (ms or 0) / fires if fires else None,
        "tokens": tokens or 0,
        "create_usd": create,
        "carry_usd": carry,
        "injected_usd": create + carry,
        "blocks": blocks,
        "retry_usd": retry,
        "errors": errors,
        "messages": msgs,
        "total_usd": create + carry + retry,
    }


def _totals(hooks: list[dict[str, Any]]) -> dict[str, Any]:
    """Summed over every hook row."""
    sums: defaultdict[str, float] = defaultdict(float)
    for row in hooks:
        for key in ("fires", "runtime_s", "tokens", "blocks", "errors"):
            sums[key] += row[key]
        for key in ("injected_usd", "retry_usd", "total_usd"):
            sums[key] += row[key]
    names = ("fires", "tokens", "blocks", "errors")
    return {
        **{key: int(sums[key]) for key in names},
        **{k: sums[k] for k in ("runtime_s", "injected_usd", "retry_usd", "total_usd")},
    }


@panel(
    "hooks",
    "Hooks",
    order=62,
    tables={t: {"limit": str(TOP)} for t in ("hooks", "stop_bounces", "budget")},
)
def build(conn: sqlite3.Connection, filters: Filters) -> dict[str, Any]:
    """Per-hook cost, Stop bounces, daily hook cost and the budget gate."""
    params = filters.params()
    hooks = [_hook(r) for r in conn.execute(_PER_HOOK, params)]
    hooks.sort(key=lambda r: (-r["total_usd"], -r["fires"], -r["errors"]))
    stops = [
        {"hook": name, "script": detail, "count": count, "retry_usd": retry or 0.0}
        for name, detail, count, retry in conn.execute(_STOPS, (*params, *STOPS))
    ]
    daily = [
        {"day": day, "injected_usd": injected or 0.0, "retry_usd": retry or 0.0}
        for day, injected, retry in conn.execute(_DAILY, params)
    ]
    budget, budget_file = _hooks_budget.read()
    return {
        "caption": CAPTION,
        "totals": {
            **_totals(hooks),
            "spend_usd": conn.execute(_SPEND, params).fetchone()[0],
        },
        "daily": daily,
        "hooks": hooks,
        "stop_bounces": stops,
        "budget": budget,
        "budget_file": budget_file,
    }
