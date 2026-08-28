"""Map request paths to JSON payloads. No I/O beyond the collectors it calls."""

from __future__ import annotations

from dataclasses import asdict
from http import HTTPStatus
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qs, urlsplit

from control_panel import _aggregate, _manifest, _rationale, _tail
from control_panel._types import to_payload

if TYPE_CHECKING:
    from control_panel._runner import CommandRunner

API_PREFIX = "/api/"


class Router:
    """Resolve API requests against a cached fleet snapshot."""

    def __init__(self, runner: CommandRunner, port: int) -> None:
        """Store the command seam and the port to report in payloads."""
        self._runner = runner
        self._port = port

    def _status(self) -> dict[str, Any]:
        """Build a fresh fleet snapshot as a JSON-ready dict."""
        return to_payload(_aggregate.build_status(self._runner, self._port))

    def resolve(self, path_and_query: str) -> tuple[HTTPStatus, dict[str, Any]] | None:
        """Return the response for an API path, or None if it is not an API path."""
        parts = urlsplit(path_and_query)
        path = parts.path
        if not path.startswith(API_PREFIX):
            return None
        segments = path[len(API_PREFIX) :].strip("/").split("/")
        head = segments[0]
        rest = segments[1] if len(segments) > 1 else ""
        if head == "health":
            return HTTPStatus.OK, {"ok": True, "port": self._port}
        if head == "status":
            return self._status_route(rest)
        if head == "logs":
            return self._logs_route(rest, parts.query)
        if head == "why":
            return self._why_route(rest)
        return HTTPStatus.NOT_FOUND, {"error": f"no such endpoint: {path}"}

    def _status_route(self, subsystem_id: str) -> tuple[HTTPStatus, dict[str, Any]]:
        """Serve the whole fleet, or one subsystem when named."""
        payload = self._status()
        if not subsystem_id:
            return HTTPStatus.OK, payload
        for subsystem in payload["subsystems"]:
            if subsystem["id"] == subsystem_id:
                return HTTPStatus.OK, subsystem
        return HTTPStatus.NOT_FOUND, {"error": f"no such subsystem: {subsystem_id}"}

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
        for subsystem in self._status()["subsystems"]:
            for ref in subsystem["logs"]:
                if ref["id"] != log_id:
                    continue
                if ref["kind"] != "file":
                    return HTTPStatus.OK, {
                        "id": log_id,
                        "kind": "journal",
                        "unit": ref["unit"],
                        "lines": [],
                        "truncated": False,
                        "note": "journal reads are not implemented yet",
                    }
                result = _tail.tail(ref["path"], lines)
                return HTTPStatus.OK, {"id": log_id, "path": ref["path"]} | asdict(
                    result
                )
        return HTTPStatus.NOT_FOUND, {"error": f"no such log: {log_id}"}


def _int_param(query: str, name: str, default: int) -> int:
    """Read one integer query parameter, falling back on anything unparsable."""
    values = parse_qs(query).get(name, ())
    if not values:
        return default
    try:
        return int(values[0])
    except ValueError:
        return default
