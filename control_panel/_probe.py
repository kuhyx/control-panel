"""Liveness probes: is anything actually answering where a server should be?

Probes were declared in the manifest from Phase 1 but never run. They matter
now that the dashboard links to every server's UI: a link to a dead port is
worse than no link.

Three rules, each from this machine:

* **Concurrent, with a short timeout.** ~30 targets probed one after another
  would stall ``/api/status`` -- and the tray, which polls it -- behind the
  slowest dead port.
* **Only local targets are probed.** A ``*.duckdns.org`` URL resolves through
  the router, which drops DNS under burst; probing public names every 30s
  would make the dashboard flap on the network instead of the service. Public
  URLs are links, reported with ``up=None``.
* **Any HTTP answer below 500 is alive.** dufs answers 401 to an anonymous
  request and that is the server working. "Is the link usable" is a separate
  question, answered by ``control-panel dashboards``.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import http.client
import ipaddress
import socket
import time
from urllib.parse import urlsplit

from control_panel._live_types import ProbeRecord

TIMEOUT_S = 1.5
MAX_WORKERS = 16
_SERVER_ERROR = 500
_LOCAL_NAMES = frozenset({"localhost"})


def is_local(host: str) -> bool:
    """Whether ``host`` is an address literal or ``localhost`` -- no DNS."""
    if host in _LOCAL_NAMES:
        return True
    try:
        ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        return False
    return True


def _elapsed_ms(started: float) -> float:
    """Milliseconds since ``started``, rounded for display."""
    return round((time.monotonic() - started) * 1000, 1)


def probe_http(url: str) -> ProbeRecord:
    """GET ``url`` without following redirects; a 3xx is an answer."""
    parts = urlsplit(url)
    host = parts.hostname or ""
    if not is_local(host):
        return ProbeRecord(
            kind="http", target=url, up=None, detail="not probed: public"
        )
    conn_type = (
        http.client.HTTPSConnection
        if parts.scheme == "https"
        else http.client.HTTPConnection
    )
    conn = conn_type(host, parts.port, timeout=TIMEOUT_S)
    started = time.monotonic()
    try:
        conn.request("GET", parts.path or "/")
        status = conn.getresponse().status
    except (OSError, http.client.HTTPException) as exc:
        return ProbeRecord(
            kind="http",
            target=url,
            up=False,
            latency_ms=_elapsed_ms(started),
            detail=str(exc),
        )
    finally:
        conn.close()
    return ProbeRecord(
        kind="http",
        target=url,
        up=status < _SERVER_ERROR,
        status=status,
        latency_ms=_elapsed_ms(started),
    )


def probe_tcp(target: str) -> ProbeRecord:
    """Open and close a TCP connection to ``host:port``."""
    host, _, port = target.rpartition(":")
    started = time.monotonic()
    try:
        with socket.create_connection((host.strip("[]"), int(port)), timeout=TIMEOUT_S):
            pass
    except (OSError, ValueError) as exc:
        return ProbeRecord(
            kind="tcp",
            target=target,
            up=False,
            latency_ms=_elapsed_ms(started),
            detail=str(exc),
        )
    return ProbeRecord(
        kind="tcp", target=target, up=True, latency_ms=_elapsed_ms(started)
    )


def probe(kind: str, target: str) -> ProbeRecord:
    """Dispatch one probe by kind; an unknown kind is reported, not raised."""
    if kind == "http":
        return probe_http(target)
    if kind == "tcp":
        return probe_tcp(target)
    return ProbeRecord(
        kind=kind, target=target, up=None, detail=f"unknown probe kind {kind!r}"
    )


def run_all(targets: list[tuple[str, str]]) -> dict[tuple[str, str], ProbeRecord]:
    """Probe every distinct ``(kind, target)`` concurrently."""
    unique = list(dict.fromkeys(targets))
    if not unique:
        return {}
    with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(unique))) as pool:
        results = pool.map(lambda pair: probe(*pair), unique)
        return dict(zip(unique, results, strict=True))
