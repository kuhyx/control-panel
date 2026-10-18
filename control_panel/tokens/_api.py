"""``/api/tokens`` routes: the panel index, one panel, one session.

    GET /api/tokens                       panels, filter options, coverage
    GET /api/tokens/panel/<name>?<filters>
    GET /api/tokens/session/<key>

Filters (all optional): ``from``/``to`` (YYYY-MM-DD, local), ``window``
(a token_audit snapshot name, for its exact window), ``cwd``, ``model``,
``scope`` (all | main | sub).
"""

from __future__ import annotations

from contextlib import closing
from http import HTTPStatus
import importlib
import json
import pkgutil
import time
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qs, unquote

from control_panel import tokens
from control_panel.tokens import _ab, _context, _db, _schema, _sessions, _tables
from control_panel.tokens._registry import PANELS, listing

if TYPE_CHECKING:
    from collections.abc import Callable
    import sqlite3

__all__ = ["route"]

Response = tuple[HTTPStatus, dict[str, Any]]
_CWD_OPTIONS = 40


def _register_all() -> list[str]:
    """Import every module of the package: importing a panel registers it.

    A new panel group is one new ``_<group>.py`` file; nothing here changes.
    """
    names = [m.name for m in pkgutil.iter_modules(tokens.__path__)]
    for name in names:
        importlib.import_module(f"{tokens.__name__}.{name}")
    return names


_register_all()


def _now() -> float:
    """Current time; a seam for tests."""
    return time.time()


def _coverage(conn: sqlite3.Connection) -> dict[str, Any]:
    """How far back each kind of data reaches."""
    detail = conn.execute("SELECT MIN(ts), MAX(ts) FROM turns").fetchone()
    aggregate = conn.execute("SELECT MIN(day) FROM aggregate_sessions").fetchone()
    prompts = conn.execute("SELECT MIN(day) FROM prompt_activity").fetchone()
    starts = [d for d in (aggregate[0], prompts[0]) if d]
    detail_from = _db.day_of(detail[0]) if detail[0] else None
    return {
        "detail_from": detail_from,
        "detail_to": _db.day_of(detail[1]) if detail[1] else None,
        "aggregate_from": aggregate[0],
        "any_from": min(
            [*starts, *([detail_from] if detail_from else [])], default=None
        ),
        "refreshed_at": float(_db.meta(conn, "refreshed_at") or 0),
        "snapshots": [
            r[0] for r in conn.execute("SELECT name FROM snapshots ORDER BY name")
        ],
    }


def _index(conn: sqlite3.Connection) -> dict[str, Any]:
    """Everything the page needs before it asks for any panel."""
    cwds = conn.execute(
        "SELECT cwd FROM session_summary WHERE cwd IS NOT NULL GROUP BY cwd"
        " ORDER BY SUM(usd) DESC LIMIT ?",
        (_CWD_OPTIONS,),
    ).fetchall()
    models = conn.execute("SELECT DISTINCT model FROM turns ORDER BY model").fetchall()
    return {
        "panels": listing(),
        "options": {
            "cwds": [r[0] for r in cwds],
            "models": [r[0] for r in models if not r[0].startswith("<")],
        },
        "coverage": _coverage(conn),
        "ab_banner": _ab.banner(conn),
        "snapshot_metrics": {
            name: json.loads(metrics or "{}")
            for name, metrics in conn.execute("SELECT name, metrics FROM snapshots")
        },
        "store": _db.store_path(),
    }


def _panel(conn: sqlite3.Connection, name: str, query: str) -> Response:
    """One registered panel under the request's filters."""
    if name not in PANELS:
        return HTTPStatus.NOT_FOUND, {"error": f"no such panel: {name}"}
    filters = _db.parse_filters(conn, query, _now())
    return HTTPStatus.OK, {
        "filters": filters.payload(),
        **PANELS[name].build(conn, filters),
    }


def _session(conn: sqlite3.Connection, key: str, _query: str) -> Response:
    """One session's drill-down."""
    found = _sessions.detail(conn, key)
    if found is None:
        return HTTPStatus.NOT_FOUND, {"error": f"no such session: {key}"}
    return HTTPStatus.OK, found


def _context_file(conn: sqlite3.Connection, _arg: str, query: str) -> Response:
    """One listed context file's content and git log."""
    path = parse_qs(query).get("path", [""])[0]
    found = _context.file_detail(conn, path)
    if found is None:
        return HTTPStatus.NOT_FOUND, {"error": "not a listed context file"}
    return HTTPStatus.OK, found


def _dispatch(conn: sqlite3.Connection, segments: list[str], query: str) -> Response:
    """Route inside an open store."""
    head = segments[0] if segments else ""
    arg = unquote("/".join(segments[1:]))
    handlers: dict[str, Callable[[], Response]] = {
        "": lambda: (HTTPStatus.OK, _index(conn)),
        "panel": lambda: _panel(conn, arg, query),
        "session": lambda: _session(conn, arg, query),
        "ab": lambda: (HTTPStatus.OK, _ab.payload(conn)),
        "context-file": lambda: _context_file(conn, arg, query),
        "schema": lambda: (HTTPStatus.OK, _schema.document(conn, _now())),
    }
    handler = handlers.get(head)
    if handler is None:
        return HTTPStatus.NOT_FOUND, {"error": f"no such tokens endpoint: {head}"}
    status, payload = handler()
    if status != HTTPStatus.OK or head == "schema":
        return status, payload
    found = PANELS.get(arg) if head == "panel" else None
    return status, _tables.apply(payload, query, found.tables if found else None)


def route(segments: list[str], query: str) -> Response:
    """Serve one /api/tokens request."""
    conn = _db.connect()
    if conn is None:
        return HTTPStatus.SERVICE_UNAVAILABLE, {
            "error": f"no token store at {_db.store_path()}: run the ingest "
            "(python3 -m python_pkg.token_dashboard.ingest in ~/src/testsAndMisc)"
        }
    with closing(conn):
        return _dispatch(conn, [s for s in segments if s], query)
