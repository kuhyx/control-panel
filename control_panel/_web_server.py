"""Loopback-only HTTP server: GET to read, POST to change one of three knobs.

Shape copied from ``steam_backlog_enforcer/_web_server.py``, which is the
in-house precedent for serving a JSON API plus a built Vite bundle from one
stdlib process.

``do_POST`` exists only to hand a JSON body to ``control_panel.mutations``; it
decides nothing itself. There is no PUT, DELETE or PATCH, and a pre-commit hook
keeps it that way.

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
from typing import IO, TYPE_CHECKING, Any
from urllib.parse import urlsplit

from control_panel import _port_guard, _routes
from control_panel._runner import SubprocessRunner

if TYPE_CHECKING:
    from collections.abc import Mapping

    from control_panel._runner import CommandRunner

logger = logging.getLogger(__name__)

# The built frontend lives at <repo>/web/dist, a sibling of the package.
WEB_DIST = (Path(__file__).resolve().parent.parent / "web" / "dist").resolve()

HOST = "127.0.0.1"
DEFAULT_PORT = 8770
# A mutation body is three integers or a hostname and a sentence.
MAX_BODY_BYTES = 64 * 1024
_EXTRA_TEXT_TYPES = frozenset(
    {"application/javascript", "application/json", "image/svg+xml"}
)
_NOT_BUILT = (
    b"Frontend not built. Run: corepack pnpm --dir web install && "
    b"corepack pnpm --dir web run build"
)


def read_json_body(headers: Mapping[str, str], stream: IO[bytes]) -> object:
    """Parse a bounded JSON request body, or None for anything unusable.

    Bounded because this listener is reachable by anything running as this
    user: a declared Content-Length of 4 GB should not become an allocation.
    Module-level rather than inside the handler closure so it is testable
    without a socket.
    """
    try:
        length = int(headers.get("Content-Length", "0"))
    except ValueError:
        return None
    if length <= 0 or length > MAX_BODY_BYTES:
        return None
    try:
        return json.loads(stream.read(length))
    except OSError, json.JSONDecodeError, ValueError:
        return None


def resolve_static(raw_path: str) -> tuple[HTTPStatus, bytes, str]:
    """Resolve a request path to a file in the built bundle.

    Anything that escapes WEB_DIST, or names a file that is not there, falls
    back to index.html so client-side routes work -- the traversal guard is the
    ``is_relative_to`` check, not the fallback.
    """
    relative = raw_path.split("?", 1)[0].lstrip("/") or "index.html"
    candidate = (WEB_DIST / relative).resolve()
    if not candidate.is_relative_to(WEB_DIST) or not candidate.is_file():
        candidate = WEB_DIST / "index.html"
    if not candidate.is_file():
        return HTTPStatus.NOT_FOUND, _NOT_BUILT, "text/plain"
    ctype, _ = mimetypes.guess_type(candidate.name)
    return HTTPStatus.OK, candidate.read_bytes(), ctype or "text/plain"


class PanelServer(ThreadingHTTPServer):
    """A loopback server that carries its router.

    The handler used to be built inside a closure over the router. Hoisting it
    to module level and hanging the router off the server keeps each method
    independently readable -- and testable without standing a server up.
    """

    router: _routes.Router


class Handler(BaseHTTPRequestHandler):
    """Serve the fleet API, the mutation endpoints and the static bundle."""

    server: PanelServer

    def log_message(self, fmt: str, /, *args: object) -> None:
        """Route the default request log to logging at debug level."""
        logger.debug("%s - %s", self.address_string(), fmt % args)

    def do_GET(self) -> None:
        """Dispatch to the API router, else serve a static file."""
        resolved = self.server.router.resolve(self.path)
        if resolved is None:
            self._send(*resolve_static(self.path))
            return
        status, payload = resolved
        self._send_json(status, payload)

    def do_POST(self) -> None:
        """Dispatch a mutation. The only write verb here.

        There is no PUT, DELETE or PATCH, and a pre-commit hook keeps it that
        way: three approved knobs need one verb between them.
        """
        path = urlsplit(self.path).path
        prefix = f"{_routes.API_PREFIX}mutate/"
        if not path.startswith(prefix):
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not a mutation"})
            return
        body = read_json_body(self.headers, self.rfile)
        status, payload = self.server.router.mutate(path[len(prefix) :], body)
        self._send_json(status, payload)

    def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        """Write a JSON response."""
        self._send(status, json.dumps(payload).encode("utf-8"), "application/json")

    def _send(self, status: HTTPStatus, body: bytes, ctype: str) -> None:
        """Write one complete response."""
        if ctype.startswith("text/") or ctype in _EXTRA_TEXT_TYPES:
            ctype = f"{ctype}; charset=utf-8"
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def create_server(runner: CommandRunner, port: int = DEFAULT_PORT) -> PanelServer:
    """Create (but do not start) the loopback server."""
    server = PanelServer((HOST, port), Handler)
    server.router = _routes.Router(runner, port)
    return server


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
