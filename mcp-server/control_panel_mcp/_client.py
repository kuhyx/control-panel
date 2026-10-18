"""HTTP access to the dashboard's ``/api/tokens`` JSON API.

The API is the single source of truth: this package never opens the SQLite
store. Every request has a timeout, and a dashboard that is not listening
becomes one actionable message instead of a stack trace.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
import http.client
import json
import os
import re
from typing import Any
from urllib.parse import parse_qsl, quote, urlencode, urlsplit

DEFAULT_URL = "http://127.0.0.1:8760"
TIMEOUT_S = 15.0
DOWN = "dashboard down: run systemctl --user start control-panel"
# The API's own filter names; anything else in a `filters` string is taken
# as a column filter on the tool's table (`t.<table>.f.<column>`).
SHARED = frozenset({"from", "to", "window", "cwd", "model", "scope"})
_DAYS = re.compile(r"^(\d+)d$")
_RANGE = re.compile(r"^(\d{4}-\d\d-\d\d)\.\.(\d{4}-\d\d-\d\d)?$")
_OK = 200
_NOT_FOUND = 404


class DashboardError(Exception):
    """The API could not answer; ``str()`` is the message for the caller."""

    def __init__(self, message: str, status: int = 0) -> None:
        """Keep the HTTP status (0 when the server was not reached)."""
        super().__init__(message)
        self.status = status


def base_url() -> str:
    """Dashboard origin (``$CONTROL_PANEL_URL`` overrides the default)."""
    return os.environ.get("CONTROL_PANEL_URL", DEFAULT_URL).rstrip("/")


def local_today() -> date:
    """Today in the local timezone (the API's day boundaries are local)."""
    return datetime.now(tz=UTC).astimezone().date()


def window_params(window: str, today: date | None = None) -> dict[str, str]:
    """Translate ``7d`` / ``2026-10-01..2026-10-07`` / a snapshot name.

    Empty means the API default (the last 30 days).
    """
    window = window.strip()
    if not window:
        return {}
    days = _DAYS.match(window)
    if days:
        start = (today or local_today()) - timedelta(days=int(days[1]) - 1)
        return {"from": start.isoformat()}
    span = _RANGE.match(window)
    if span:
        return {"from": span[1], **({"to": span[2]} if span[2] else {})}
    return {"window": window}


def filter_params(filters: str, table: str) -> dict[str, str]:
    """Split a ``k=v&k=v`` string into shared filters and column filters."""
    out: dict[str, str] = {}
    for key, value in parse_qsl(filters.strip().lstrip("?")):
        if key == "window":
            out.update(window_params(value))
        elif key in SHARED:
            out[key] = value
        else:
            out[f"t.{table}.f.{key}"] = value
    return out


def table_params(table: str, search: str, sort: str, limit: int) -> dict[str, str]:
    """The API's uniform table grammar for one table."""
    params = {"q": search, "sort": sort, "limit": str(limit) if limit else ""}
    return {f"t.{table}.{k}": v for k, v in params.items() if v}


def get(path: str, params: dict[str, str] | None = None) -> dict[str, Any]:
    """GET ``/api/tokens<path>`` and return the decoded JSON object.

    Raises:
        DashboardError: server down, non-200 answer, or a body that is not
            a JSON object.
    """
    parts = urlsplit(base_url())
    query = urlencode({k: v for k, v in (params or {}).items() if v})
    target = quote(f"/api/tokens{path}", safe="/") + (f"?{query}" if query else "")
    conn = http.client.HTTPConnection(
        parts.hostname or "127.0.0.1", parts.port or 80, timeout=TIMEOUT_S
    )
    try:
        conn.request("GET", target)
        response = conn.getresponse()
        status, body = response.status, response.read()
    except (OSError, http.client.HTTPException) as exc:
        msg = f"{DOWN} ({type(exc).__name__}: {exc})"
        raise DashboardError(msg) from exc
    finally:
        conn.close()
    try:
        data = json.loads(body)
    except ValueError as exc:
        msg = f"HTTP {status}: response is not JSON"
        raise DashboardError(msg, status) from exc
    if not isinstance(data, dict):
        msg = f"HTTP {status}: expected a JSON object"
        raise DashboardError(msg, status)
    if status != _OK:
        msg = f"HTTP {status}: {data.get('error', 'request failed')}"
        raise DashboardError(msg, status)
    return data


def is_missing(error: DashboardError) -> bool:
    """True when the endpoint/panel does not exist (yet)."""
    return error.status == _NOT_FOUND
