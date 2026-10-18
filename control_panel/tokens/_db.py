"""Shared query layer for the /tokens panels: the store, and the filters.

The store is written by ``python_pkg.token_dashboard.ingest`` in testsAndMisc
(a user timer); this side only ever opens it read-only. Every filter is a
bound parameter in one static WHERE clause -- an empty value disables it -- so
no panel ever builds SQL from strings.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
import json
import os
import sqlite3
from typing import Any
from urllib.parse import parse_qs

from control_panel import _sysroot

STORE = "data/token-dashboard/tokens.sqlite"
DEFAULT_DAYS = 30
SCOPES = {"all": -1, "main": 0, "sub": 1}

# Every panel query over turns (and calls / marks / turn_detail) ends with the
# shared filter clause -- ts in range, cwd equal to or under the cwd filter,
# model equal, is_sub matching the scope -- written as the same two literal
# lines in every module (see _carry.py; never assembled from strings), and
# binds Filters.params(). Two lines, not four: pylint's duplicate-code check
# runs over all files at once and flags four identical lines.


@dataclass(frozen=True)
class Filters:
    """Date range, repo/cwd, model and main-vs-subagent scope."""

    since: float
    until: float
    cwd: str = ""
    model: str = ""
    scope: str = "all"
    # The request's raw query string, for panel-specific parameters (e.g.
    # anomalies' ``over``); never part of the shared SQL clause.
    query: str = ""

    def params(self) -> tuple[object, ...]:
        """Bind values for the shared turns filter clause, in order."""
        flag = SCOPES.get(self.scope, -1)
        return (
            self.since,
            self.until,
            self.cwd,
            self.cwd,
            self.cwd,
            self.model,
            self.model,
            flag,
            flag,
        )

    def payload(self) -> dict[str, Any]:
        """The filters as the frontend sees them."""
        return {
            "since": self.since,
            "until": self.until,
            "cwd": self.cwd,
            "model": self.model,
            "scope": self.scope,
        }


def store_path() -> str:
    """Where the store lives (under the test root in tests)."""
    return str(_sysroot.user_path(STORE))


def connect() -> sqlite3.Connection | None:
    """Open the store read-only, or ``None`` when it has not been built."""
    try:
        return sqlite3.connect(f"file:{store_path()}?mode=ro", uri=True)
    except sqlite3.OperationalError:
        return None


def _first(query: dict[str, list[str]], name: str) -> str:
    """One query-string value, empty when absent."""
    return query.get(name, [""])[0]


def _day_start(text: str) -> float | None:
    """Local midnight of a ``YYYY-MM-DD`` day, ``None`` if unparsable."""
    try:
        day = date.fromisoformat(text)
    except ValueError:
        return None
    return datetime.combine(day, datetime.min.time()).astimezone().timestamp()


def _snapshot_window(conn: sqlite3.Connection, name: str) -> tuple[float, float] | None:
    """A token_audit snapshot's exact window, for reconciling against it."""
    row = conn.execute(
        "SELECT since, until FROM snapshots WHERE name = ?", (name,)
    ).fetchone()
    return (float(row[0]), float(row[1])) if row and row[0] is not None else None


def parse_filters(conn: sqlite3.Connection, raw: str, now: float) -> Filters:
    """Read filters from a query string; defaults to the last 30 days."""
    query = parse_qs(raw)
    window = _snapshot_window(conn, _first(query, "window"))
    if window is not None:
        since, until = window
    else:
        start = _day_start(_first(query, "from"))
        end = _day_start(_first(query, "to"))
        until = end + timedelta(days=1).total_seconds() - 1 if end else now
        since = start if start is not None else until - DEFAULT_DAYS * 86400
    scope = _first(query, "scope") or "all"
    return Filters(
        since=since,
        until=until,
        cwd=_first(query, "cwd").rstrip("/"),
        model=_first(query, "model"),
        scope=scope if scope in SCOPES else "all",
        query=raw,
    )


def meta(conn: sqlite3.Connection, key: str) -> str | None:
    """One value from the store's ``meta`` table."""
    row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return str(row[0]) if row else None


def meta_json(conn: sqlite3.Connection, key: str) -> object:
    """A JSON value from ``meta``, ``None`` when absent."""
    raw = meta(conn, key)
    return json.loads(raw) if raw else None


def ratio(part: float, whole: float) -> float | None:
    """``part / whole`` or ``None`` when ``whole`` is zero."""
    return part / whole if whole else None


def home() -> str:
    """The user's home directory, for the "sessions started in ~" share."""
    return os.environ.get("HOME", "/root").rstrip("/")


def day_of(stamp: float) -> str:
    """Local calendar day of a unix timestamp."""
    return datetime.fromtimestamp(stamp).astimezone().strftime("%Y-%m-%d")


def monday(day: str) -> str:
    """Monday of the week containing a ``YYYY-MM-DD`` day."""
    parsed = date.fromisoformat(day)
    return (parsed - timedelta(days=parsed.weekday())).isoformat()
