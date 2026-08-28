from __future__ import annotations

import http.client
import json
import threading
from typing import TYPE_CHECKING

import pytest

from control_panel import _port_guard, _web_server
from control_panel.tests._fixture_runner import FakeRunner, ok

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


@pytest.fixture
def served(monkeypatch: pytest.MonkeyPatch) -> Iterator[int]:
    """Run the real server on an ephemeral port."""
    monkeypatch.setattr(
        _web_server._routes.Router,
        "_status",
        lambda _self: {"subsystems": [], "rollup": {}},
    )
    server = _web_server.create_server(FakeRunner({}), 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def get(port: int, path: str) -> tuple[int, bytes, str]:
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request("GET", path)
    response = conn.getresponse()
    body = response.read()
    ctype = response.headers.get("Content-Type", "")
    conn.close()
    return response.status, body, ctype


def test_serves_the_api(served: int) -> None:
    status, body, ctype = get(served, "/api/health")
    assert status == 200
    assert json.loads(body)["ok"] is True
    assert ctype == "application/json; charset=utf-8"


def test_unknown_api_path_is_404(served: int) -> None:
    status, _, _ = get(served, "/api/nope")
    assert status == 404


def test_binds_loopback_only() -> None:
    # The payload names every enforcement mechanism and which are off. There
    # is no auth, so the bind address is the entire access control.
    assert _web_server.HOST == "127.0.0.1"


def test_post_is_the_only_write_verb() -> None:
    # Three approved knobs need one verb between them. PUT/DELETE/PATCH would
    # each be a shape this dashboard has no business offering.
    assert hasattr(_web_server.Handler, "do_POST")
    for verb in ("do_PUT", "do_DELETE", "do_PATCH"):
        assert not hasattr(_web_server.Handler, verb)


def test_missing_bundle_explains_how_to_build_it(
    served: int, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # web/dist really exists in a built checkout, so point at an empty one.
    monkeypatch.setattr(_web_server, "WEB_DIST", (tmp_path / "unbuilt").resolve())
    status, body, _ = get(served, "/")
    assert status == 404
    assert b"pnpm" in body


def test_serves_the_bundle_and_falls_back_to_index(
    served: int, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<!doctype html><title>cp</title>")
    (dist / "app.js").write_text("console.log(1)")
    monkeypatch.setattr(_web_server, "WEB_DIST", dist.resolve())
    assert get(served, "/app.js")[1] == b"console.log(1)"
    # SPA fallback: an unknown route serves index.html rather than 404.
    assert b"<!doctype html>" in get(served, "/s/hosts")[1]


def test_path_traversal_falls_back_to_index(
    served: int, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("safe")
    (tmp_path / "secret.txt").write_text("SECRET")
    monkeypatch.setattr(_web_server, "WEB_DIST", dist.resolve())
    assert get(served, "/../secret.txt")[1] == b"safe"


def test_request_logging_is_routed_to_the_logger(
    served: int, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level("DEBUG", logger="control_panel._web_server"):
        get(served, "/api/health")
    assert any("GET /api/health" in r.getMessage() for r in caplog.records)


def test_serve_refuses_a_taken_port_instead_of_reaping(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def taken(*_args: object, **_kwargs: object) -> None:
        raise OSError(_port_guard.EADDRINUSE, "Address already in use")

    monkeypatch.setattr(_web_server, "create_server", taken)
    ss = ("ss", "-tlnp")
    monkeypatch.setattr(
        _web_server,
        "SubprocessRunner",
        lambda: FakeRunner(
            {
                ss: ok(
                    ss, 'LISTEN 0 5 127.0.0.1:8770 0.0.0.0:* users:(("x",pid=42,fd=3))'
                )
            }
        ),
    )
    assert _web_server.serve(8770) == 1
    assert "pid 42" in capsys.readouterr().err


def test_other_oserrors_are_not_swallowed(monkeypatch: pytest.MonkeyPatch) -> None:
    def denied(*_args: object, **_kwargs: object) -> None:
        raise OSError(13, "Permission denied")

    monkeypatch.setattr(_web_server, "create_server", denied)
    with pytest.raises(OSError, match="Permission denied"):
        _web_server.serve(80)


def test_serve_runs_until_interrupted(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    class Fake:
        def __init__(self) -> None:
            self.closed = False

        def serve_forever(self) -> None:
            raise KeyboardInterrupt

        def server_close(self) -> None:
            self.closed = True

    made = Fake()
    monkeypatch.setattr(_web_server, "create_server", lambda *_a, **_k: made)
    assert _web_server.serve(8770) == 0
    assert made.closed
    assert "Shutting down" in capsys.readouterr().out


def test_binary_assets_keep_their_content_type_without_a_charset(
    served: int, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("x")
    (dist / "icon.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    monkeypatch.setattr(_web_server, "WEB_DIST", dist.resolve())
    _status, body, ctype = get(served, "/icon.png")
    assert ctype == "image/png"
    assert body.startswith(b"\x89PNG")
