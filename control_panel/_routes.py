"""Map request paths to JSON payloads. No I/O beyond the collectors it calls."""

from __future__ import annotations

from dataclasses import asdict
from http import HTTPStatus
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qs, urlsplit

from control_panel import (
    _aggregate,
    _journal,
    _manifest,
    _rationale,
    _snapshot,
    _tail,
    _tray_model,
    _unknown,
)
from control_panel._types import to_payload
from control_panel.mutations import (
    _hosts_add,
    _restart,
    _session_delete,
    _session_mark,
    _session_resume,
    _shutdown_hours,
    _steam_view,
)
from control_panel.mutations import _types as _mutation_types
from control_panel.sessions import _api as _sessions_api
from control_panel.tokens import _api as _tokens_api

if TYPE_CHECKING:
    from control_panel._runner import CommandRunner

API_PREFIX = "/api/"
# /api/journal/<source>/<name>: a scope or "docker", then a unit or container.
_JOURNAL_SEGMENTS = 2
# Mutations that cannot change fleet state, so they skip the ~2 s re-collect.
_FLEET_NEUTRAL = frozenset({"session-resume", "session-mark", "session-delete"})


class Router:
    """Resolve API requests against a cached fleet snapshot."""

    def __init__(
        self,
        runner: CommandRunner,
        port: int,
        snapshot: _snapshot.SnapshotCache | None = None,
    ) -> None:
        """Store the command seam, the port, and the snapshot cache.

        The default cache starts no thread: it builds on first read and after
        a mutation. ``serve()`` starts its background collector.
        """
        self._runner = runner
        self._port = port
        if snapshot is None:
            snapshot = _snapshot.SnapshotCache(self._build_status)
        self.snapshot = snapshot

    def _build_status(self) -> dict[str, Any]:
        """Collect a fresh fleet snapshot as a JSON-ready dict (slow: ~2 s)."""
        return to_payload(_aggregate.build_status(self._runner, self._port))

    def _status(self, *, watching: bool = True) -> dict[str, Any]:
        """Return the cached fleet snapshot, building it only if none exists."""
        return self.snapshot.get(watching=watching)

    def resolve(self, path_and_query: str) -> tuple[HTTPStatus, dict[str, Any]] | None:
        """Return the response for an API path, or None if it is not one."""
        parts = urlsplit(path_and_query)
        path = parts.path
        if not path.startswith(API_PREFIX):
            return None
        segments = path[len(API_PREFIX) :].strip("/").split("/")
        head = segments[0]
        rest = segments[1] if len(segments) > 1 else ""
        if head == "health":
            return HTTPStatus.OK, {"ok": True, "port": self._port}
        # A table rather than a return ladder: adding a route should not make
        # this function harder to read.
        routes = {
            "status": self._status_route,
            "why": self._why_route,
            "mutate": self._mutate_get,
            "logs": lambda name: self._logs_route(name, parts.query),
            "journal": lambda _: self._journal_route(segments[1:], parts.query),
            "unknown": lambda _: self._unknown_route(),
            "tray": lambda _: self._tray_route(),
            "tokens": lambda _: _tokens_api.route(segments[1:], parts.query),
            "sessions": lambda _: _sessions_api.route(segments[1:], parts.query),
        }
        handler = routes.get(head)
        if handler is None:
            return HTTPStatus.NOT_FOUND, {"error": f"no such endpoint: {path}"}
        return handler(rest)

    def _status_route(self, subsystem_id: str) -> tuple[HTTPStatus, dict[str, Any]]:
        """Serve the whole fleet, or one subsystem when named."""
        payload = self._status()
        if not subsystem_id:
            return HTTPStatus.OK, payload
        for subsystem in payload["subsystems"]:
            if subsystem["id"] == subsystem_id:
                return HTTPStatus.OK, subsystem
        return HTTPStatus.NOT_FOUND, {"error": f"no such subsystem: {subsystem_id}"}

    # POST bodies are dispatched here. The table is explicit rather than
    # derived from the path, so a typo cannot invent an endpoint.
    def mutate(self, name: str, body: object) -> tuple[HTTPStatus, dict[str, Any]]:
        """Apply one of the six approved changes, or refuse to know it."""
        handlers = {
            "shutdown-hours": _shutdown_hours.apply,
            "hosts-add": _hosts_add.apply,
            "restart": _restart.apply,
            # Approved by kuhy on 2026-10-22 for the sessions tab.
            "session-resume": _session_resume.apply,
            "session-mark": _session_mark.apply,
            "session-delete": _session_delete.apply,
        }
        handler = handlers.get(name)
        if handler is None:
            return HTTPStatus.NOT_FOUND, {"error": f"no such mutation: {name}"}
        result = handler(self._runner, body)
        if name in _FLEET_NEUTRAL:
            return HTTPStatus.OK, _mutation_types.to_payload(result)
        # Answer only once the snapshot reflects the change, so the next GET
        # shows it instead of the up-to-10 s-old state from before.
        self.snapshot.refresh_if_warm()
        # A refusal is the guard working, so it is a 200 carrying the script's
        # own words -- not a 4xx, which would read as "the dashboard is broken".
        return HTTPStatus.OK, _mutation_types.to_payload(result)

    def _mutate_get(self, name: str) -> tuple[HTTPStatus, dict[str, Any]]:
        """Serve the read-only half of the mutation surface."""
        if name == "steam-exceptions":
            return HTTPStatus.OK, _steam_view.view()
        return HTTPStatus.NOT_FOUND, {
            "error": f"{name} is not readable; POST /api/mutate/{name} to change it"
        }

    def _why_route(self, subsystem_id: str) -> tuple[HTTPStatus, dict[str, Any]]:
        """Explain why one subsystem is enforced, from docs and the sidecar."""
        for entry in _manifest.load_manifest():
            if entry.id == subsystem_id:
                built = _rationale.build(self._runner, entry)
                return HTTPStatus.OK, _rationale.to_payload(built)
        return HTTPStatus.NOT_FOUND, {"error": f"no such subsystem: {subsystem_id}"}

    def _logs_route(self, log_id: str, query: str) -> tuple[HTTPStatus, dict[str, Any]]:
        """Serve a bounded tail of one declared log."""
        if not log_id:
            return HTTPStatus.NOT_FOUND, {"error": "no log id given"}
        lines = _int_param(query, "lines", _tail.DEFAULT_LINES)
        # From the manifest, not the snapshot: a log spec is declared, not
        # collected, and reading it must not wait on a fleet collection.
        for entry in _manifest.load_manifest():
            for declared in entry.logs:
                if declared.id != log_id:
                    continue
                if declared.kind != "file":
                    return self._journal_route(
                        [str(declared.scope), declared.unit], query
                    )
                result = _tail.tail(declared.path, lines)
                return HTTPStatus.OK, {"id": log_id, "path": declared.path} | asdict(
                    result
                )
        return HTTPStatus.NOT_FOUND, {"error": f"no such log: {log_id}"}

    def _journal_route(
        self, segments: list[str], query: str
    ) -> tuple[HTTPStatus, dict[str, Any]]:
        """Tail a declared unit's journal or a declared container's log."""
        if len(segments) != _JOURNAL_SEGMENTS:
            return HTTPStatus.NOT_FOUND, {
                "error": "expected /api/journal/<source>/<name>"
            }
        source, name = segments
        lines = _int_param(query, "lines", _journal.DEFAULT_LINES)
        read = _journal.read(
            self._runner, _manifest.load_manifest(), source, name, lines
        )
        if read is None:
            return HTTPStatus.NOT_FOUND, {"error": f"{source}/{name} is not declared"}
        return HTTPStatus.OK, read

    def _unknown_route(self) -> tuple[HTTPStatus, dict[str, Any]]:
        """List listeners and user units that no manifest entry declares."""
        entries = _manifest.load_manifest()
        listeners = _unknown.unknown_listeners(
            self._runner, entries, _manifest.load_ignored_listeners(), self._port
        )
        return HTTPStatus.OK, {
            "listeners": [asdict(item) for item in listeners],
            "units": [asdict(item) for item in _unknown.undeclared_units(entries)],
        }

    def _tray_route(self) -> tuple[HTTPStatus, dict[str, Any]]:
        """Serve the tray icon's whole view, decided server-side."""
        panel_url = f"http://127.0.0.1:{self._port}/"
        return HTTPStatus.OK, _tray_model.build(self._status(watching=False), panel_url)


def _int_param(query: str, name: str, default: int) -> int:
    """Read one integer query parameter, falling back on anything unparsable."""
    values = parse_qs(query).get(name, ())
    if not values:
        return default
    try:
        return int(values[0])
    except ValueError:
        return default
