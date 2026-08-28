"""Loopback-only HTTP server. Read-only: there is no ``do_POST``.

Shape copied from ``steam_backlog_enforcer/_web_server.py``, which is the
in-house precedent for serving a JSON API plus a built Vite bundle from one
stdlib process.

Binding is ``127.0.0.1`` and that is not configurable. The payload names every
enforcement mechanism on the machine, which unit is unarmed, and where each
policy file lives -- a map of exactly what to switch off. On a routable address
that is a gift to anything on the network, and there is no authentication here
to stop it.
"""

from __future__ import annotations

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import logging
import mimetypes
from pathlib import Path
import sys
from typing import TYPE_CHECKING

from control_panel import _port_guard, _routes
from control_panel._runner import SubprocessRunner

if TYPE_CHECKING:
    from control_panel._runner import CommandRunner

logger = logging.getLogger(__name__)

# The built frontend lives at <repo>/web/dist, a sibling of the package.
WEB_DIST = (Path(__file__).resolve().parent.parent / "web" / "dist").resolve()

HOST = "127.0.0.1"
DEFAULT_PORT = 8770
_EXTRA_TEXT_TYPES = frozenset(
    {"application/javascript", "application/json", "image/svg+xml"}
)
_NOT_BUILT = (
    b"Frontend not built. Run: corepack pnpm --dir web install && "
    b"corepack pnpm --dir web run build"
)


def make_handler(router: _routes.Router) -> type[BaseHTTPRequestHandler]:
    """Build a handler class bound to one router instance."""

    class _Handler(BaseHTTPRequestHandler):
        """Serve the fleet API and the static frontend bundle. GET only."""

        def log_message(self, fmt: str, *args: object) -> None:
            """Route the default request log to logging at debug level."""
            logger.debug("%s - %s", self.address_string(), fmt % args)

        def do_GET(self) -> None:
            """Dispatch to the API router, else serve a static file."""
            resolved = router.resolve(self.path)
            if resolved is None:
                self._serve_static(self.path)
                return
            status, payload = resolved
            self._send(status, json.dumps(payload).encode("utf-8"), "application/json")

        def _serve_static(self, raw_path: str) -> None:
            """Serve from WEB_DIST with SPA fallback and a traversal guard."""
            relative = raw_path.split("?", 1)[0].lstrip("/") or "index.html"
            candidate = (WEB_DIST / relative).resolve()
            if not candidate.is_relative_to(WEB_DIST) or not candidate.is_file():
                candidate = WEB_DIST / "index.html"
            if not candidate.is_file():
                self._send(HTTPStatus.NOT_FOUND, _NOT_BUILT, "text/plain")
                return
            ctype, _ = mimetypes.guess_type(candidate.name)
            self._send(HTTPStatus.OK, candidate.read_bytes(), ctype or "text/plain")

        def _send(self, status: HTTPStatus, body: bytes, ctype: str) -> None:
            """Write one complete response."""
            if ctype.startswith("text/") or ctype in _EXTRA_TEXT_TYPES:
                ctype = f"{ctype}; charset=utf-8"
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return _Handler


def create_server(
    runner: CommandRunner, port: int = DEFAULT_PORT
) -> ThreadingHTTPServer:
    """Create (but do not start) the loopback server."""
    return ThreadingHTTPServer((HOST, port), make_handler(_routes.Router(runner, port)))


def serve(port: int = DEFAULT_PORT) -> int:
    """Run until interrupted. Returns a process exit code."""
    runner = SubprocessRunner()
    try:
        server = create_server(runner, port)
    except OSError as exc:
        if exc.errno != _port_guard.EADDRINUSE:
            raise
        sys.stderr.write(_port_guard.refusal_message(runner, port) + "\n")
        return 1
    sys.stdout.write(f"control-panel: http://{HOST}:{port}  (Ctrl-C to stop)\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        sys.stdout.write("\nShutting down.\n")
    finally:
        server.server_close()
    return 0
