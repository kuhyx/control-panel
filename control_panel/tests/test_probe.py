from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import socket
import threading
from typing import TYPE_CHECKING

import pytest

from control_panel import _probe

if TYPE_CHECKING:
    from collections.abc import Iterator


class _Handler(BaseHTTPRequestHandler):
    """Answer /ok with 200, /broken with 500, anything else with 401."""

    def do_GET(self) -> None:
        code = {"/ok": 200, "/broken": 500}.get(self.path, 401)
        self.send_response(code)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, fmt: str, /, *args: object) -> None:
        del fmt, args


@pytest.fixture
def server() -> Iterator[int]:
    """A real loopback HTTP server on a kernel-assigned port."""
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield httpd.server_address[1]
    httpd.shutdown()
    httpd.server_close()


def _closed_port() -> int:
    """A port nothing listens on: bind, read it, release it."""
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.mark.parametrize("host", ["localhost", "127.0.0.1", "[::1]", "100.109.64.41"])
def test_address_literals_and_localhost_are_local(host: str) -> None:
    assert _probe.is_local(host)


def test_a_dns_name_is_not_local() -> None:
    assert not _probe.is_local("kuhy.duckdns.org")


def test_http_ok(server: int) -> None:
    record = _probe.probe_http(f"http://127.0.0.1:{server}/ok")
    assert record.up is True
    assert record.status == 200
    assert record.latency_ms is not None


def test_http_401_is_alive(server: int) -> None:
    record = _probe.probe_http(f"http://127.0.0.1:{server}/login")
    assert (record.up, record.status) == (True, 401)


def test_http_500_is_down(server: int) -> None:
    record = _probe.probe_http(f"http://127.0.0.1:{server}/broken")
    assert (record.up, record.status) == (False, 500)


def test_http_empty_path_requests_root(server: int) -> None:
    assert _probe.probe_http(f"http://127.0.0.1:{server}").status == 401


def test_http_refused() -> None:
    record = _probe.probe_http(f"http://127.0.0.1:{_closed_port()}/")
    assert record.up is False
    assert record.detail


def test_https_to_plain_server_is_down(server: int) -> None:
    assert _probe.probe_http(f"https://127.0.0.1:{server}/").up is False


def test_public_url_is_not_probed() -> None:
    record = _probe.probe_http("https://kuhy.duckdns.org/")
    assert record.up is None
    assert record.detail == "not probed: public"


def test_tcp_up_and_down(server: int) -> None:
    assert _probe.probe_tcp(f"127.0.0.1:{server}").up is True
    assert _probe.probe_tcp(f"127.0.0.1:{_closed_port()}").up is False
    assert _probe.probe_tcp("127.0.0.1:notaport").up is False


def test_dispatch_and_unknown_kind(server: int) -> None:
    assert _probe.probe("tcp", f"127.0.0.1:{server}").up is True
    assert _probe.probe("http", f"http://127.0.0.1:{server}/ok").up is True
    unknown = _probe.probe("icmp", "x")
    assert unknown.up is None
    assert "unknown probe kind" in (unknown.detail or "")


def test_run_all_dedupes_and_handles_empty(server: int) -> None:
    assert _probe.run_all([]) == {}
    target = ("tcp", f"127.0.0.1:{server}")
    results = _probe.run_all([target, target])
    assert list(results) == [target]
    assert results[target].up is True
