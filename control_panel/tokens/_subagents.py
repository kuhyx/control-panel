"""Subagents: what each kind of agent cost and how much it handed back.

The agent set comes from ``turns`` (``is_sub = 1``) under every filter; the
metadata (type, description, wall/active time) is joined from
``subagent_link`` outside the filtered subquery. *Leverage* joins the
parent's Agent/Task call (``calls`` x ``agent_calls`` on key + ts) to the
agent it spawned: tokens returned to the parent / tokens the agent spent.
"""

from __future__ import annotations

from collections import defaultdict
import dataclasses
from typing import TYPE_CHECKING, Any

from control_panel.tokens._db import ratio
from control_panel.tokens._registry import panel
from control_panel.tokens._subagents_routing import routing

if TYPE_CHECKING:
    import sqlite3

    from control_panel.tokens._db import Filters

TOP = 25
UNLINKED = "(unlinked)"
CAPTION = (
    "Leverage = tokens returned to the parent (the Agent call's result, "
    "estimated at 4 chars/token) / tokens the subagent spent (input + cache "
    "read + cache write + output over its calls). 0.01 means 100 tokens read "
    "per token handed back: that is the point of a search agent (the reading "
    "stays out of the parent's context); a high value means a big answer that "
    "lands in the parent's context anyway. USD and calls are the agent's calls "
    "inside the filters; wall / active time is the whole agent's. The return "
    "lookup ignores the model and scope filters (the parent's model differs)."
)

_AGENTS = (
    "WITH t AS (SELECT key, MAX(model) AS model, SUM(usd) AS usd,"
    " COUNT(*) AS n, SUM(input + cache_read + cache_write + output) AS tok"
    " FROM turns WHERE"
    " ts BETWEEN ? AND ?"
    " AND (? = '' OR cwd = ? OR cwd LIKE ? || '/%')"
    " AND (? = '' OR model = ?)"
    " AND (? = -1 OR is_sub = ?)"
    " AND is_sub = 1 GROUP BY key)"
    " SELECT t.key, l.agent_type, COALESCE(l.model, t.model), l.description,"
    " t.usd, t.n, t.tok, l.wall_s, l.active_s"
    " FROM t LEFT JOIN subagent_link AS l ON l.sub_key = t.key"
)
_SPAWNS = (
    "SELECT c.main_key || '/agent-' || a.agent_id, c.key, c.day, c.target,"
    " c.result_tokens FROM (SELECT key, main_key, ts, day, target, result_tokens"
    " FROM calls WHERE name IN ('Agent', 'Task') AND"
    " ts BETWEEN ? AND ?"
    " AND (? = '' OR cwd = ? OR cwd LIKE ? || '/%')"
    " AND (? = '' OR model = ?)"
    " AND (? = -1 OR is_sub = ?)"
    ") AS c LEFT JOIN agent_calls AS a ON a.key = c.key AND a.ts = c.ts"
)
_GROUPS = {"by_type": 0, "by_model": 1, "by_description": 2}


def _agent_row(row: tuple[Any, ...], returned: int) -> dict[str, Any]:
    """One subagent's numbers; ``groups`` = (type, model, description)."""
    key, kind, model, desc, usd, calls, spent, wall, active = row
    return {
        "key": key,
        "groups": (kind or UNLINKED, model, desc or UNLINKED),
        "agents": 1,
        "usd": usd,
        "calls": calls,
        "wall_s": wall or 0.0,
        "active_s": active or 0.0,
        "returned_tokens": returned,
        "spent_tokens": spent or 0,
    }


def _agents(conn: sqlite3.Connection, filters: Filters) -> list[dict[str, Any]]:
    """One row per subagent inside the filters, with what it returned."""
    unscoped = dataclasses.replace(filters, model="", scope="all")
    returned: defaultdict[str, int] = defaultdict(int)
    for sub_key, *_, tokens in conn.execute(_SPAWNS, unscoped.params()):
        returned[sub_key] += tokens or 0
    return [
        _agent_row(row, returned.get(row[0], 0))
        for row in conn.execute(_AGENTS, filters.params())
    ]


SUMMED = ("agents", "usd", "calls", "wall_s", "active_s")
TOKENS = ("returned_tokens", "spent_tokens")


def _sum(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Totals of the summable columns, plus the leverage ratio."""
    out = {name: sum(r[name] for r in rows) for name in (*SUMMED, *TOKENS)}
    out["leverage"] = ratio(out["returned_tokens"], out["spent_tokens"])
    return out


def _grouped(rows: list[dict[str, Any]], at: int) -> list[dict[str, Any]]:
    """Agents grouped by type / model / description, the costliest first."""
    groups: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[row["groups"][at]].append(row)
    out = [{"label": label, **_sum(members)} for label, members in groups.items()]
    return sorted(out, key=lambda r: (-r["usd"], r["label"]))


def _worktree(
    conn: sqlite3.Connection, filters: Filters, usd: dict[str, float]
) -> list[dict[str, Any]]:
    """Agent spawns into a git worktree, with the spawned agent's cost."""
    rows = [
        {
            "day": day,
            "key": key,
            "target": target,
            "sub_key": sub_key or "",
            "usd": usd.get(sub_key or ""),
        }
        for sub_key, key, day, target, _ in conn.execute(_SPAWNS, filters.params())
        if target.endswith("[worktree]")
    ]
    return sorted(rows, key=lambda r: (-(r["usd"] or 0.0), r["day"]))


TABLES = ("by_type", "by_model", "by_description", "worktree", "routing.ab")


@panel(
    "subagents",
    "Subagents",
    order=74,
    tables={t: {"limit": str(TOP)} for t in TABLES},
)
def build(conn: sqlite3.Connection, filters: Filters) -> dict[str, Any]:
    """Subagent cost and leverage by type / model / description."""
    agents = _agents(conn, filters)
    worktree = _worktree(conn, filters, {a["key"]: a["usd"] for a in agents})
    return {
        "caption": CAPTION,
        "totals": {**_sum(agents), "worktree_agents": len(worktree)},
        **{name: _grouped(agents, at) for name, at in _GROUPS.items()},
        "worktree": worktree,
        "routing": routing(conn, filters),
    }
