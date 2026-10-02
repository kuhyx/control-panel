"""POST transport tests.

Split from test_web_server.py: the read path and the write path are different
concerns, and the combined file was over the 250-line cap.
"""

from __future__ import annotations

from http import HTTPStatus
import http.client
import io
import json
import threading
from typing import TYPE_CHECKING

import pytest

from control_panel import _web_server
from control_panel.tests._fixture_runner import FakeRunner

if TYPE_CHECKING:
    from collections.abc import Iterator


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


def post(
    port: int, path: str, body: bytes | None, ctype: str = "application/json"
) -> tuple[int, bytes]:
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    headers = {"Content-Type": ctype}
    conn.request("POST", path, body=body, headers=headers)
    response = conn.getresponse()
    data = response.read()
    conn.close()
    return response.status, data


def test_post_reaches_the_mutation_router(
    served: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[tuple[str, object]] = []

    def record(
        _self: object, name: str, body: object
    ) -> tuple[object, dict[str, object]]:
        seen.append((name, body))
        return HTTPStatus.OK, {"ok": True}

    monkeypatch.setattr(_web_server._routes.Router, "mutate", record)
    status, data = post(served, "/api/mutate/shutdown-hours", b'{"mon_wed_hour": 21}')
    assert status == 200
    assert json.loads(data)["ok"] is True
    assert seen == [("shutdown-hours", {"mon_wed_hour": 21})]


def test_post_outside_the_mutate_prefix_is_404(served: int) -> None:
    status, _ = post(served, "/api/status", b"{}")
    assert status == 404


def test_an_oversized_body_is_not_read(
    served: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[object] = []

    def record(
        _self: object, _name: str, parsed: object
    ) -> tuple[object, dict[str, object]]:
        seen.append(parsed)
        return HTTPStatus.OK, {}

    monkeypatch.setattr(_web_server._routes.Router, "mutate", record)
    # Declared far larger than the cap: the handler must not allocate it.
    conn = http.client.HTTPConnection("127.0.0.1", served, timeout=5)
    conn.request(
        "POST",
        "/api/mutate/hosts-add",
        body=b"{}",
        headers={
            "Content-Length": str(_web_server.MAX_BODY_BYTES + 1),
            "Content-Type": "application/json",
        },
    )
    conn.getresponse().read()
    conn.close()
    assert seen == [None]


@pytest.mark.parametrize("body", [b"", b"not json", None])
def test_a_malformed_body_arrives_as_none(
    served: int, monkeypatch: pytest.MonkeyPatch, body: bytes | None
) -> None:
    seen: list[object] = []

    def record(
        _self: object, _name: str, parsed: object
    ) -> tuple[object, dict[str, object]]:
        seen.append(parsed)
        return HTTPStatus.OK, {}

    monkeypatch.setattr(_web_server._routes.Router, "mutate", record)
    post(served, "/api/mutate/hosts-add", body)
    assert seen == [None]


@pytest.mark.parametrize(
    ("headers", "payload", "expected"),
    [
        ({"Content-Length": "2"}, b"{}", {}),
        ({"Content-Length": "13"}, b'{"a": [1, 2]}', {"a": [1, 2]}),
        ({}, b"", None),
        ({"Content-Length": "0"}, b"", None),
        ({"Content-Length": "-5"}, b"", None),
        ({"Content-Length": "abc"}, b"", None),
        ({"Content-Length": "8"}, b"not json", None),
    ],
)
def test_read_json_body_covers_every_shape(
    headers: dict[str, str], payload: bytes, expected: object
) -> None:
    assert _web_server.read_json_body(headers, io.BytesIO(payload)) == expected


def test_read_json_body_survives_a_stream_that_errors() -> None:
    class Broken(io.BytesIO):
        def read(self, _size: int | None = -1) -> bytes:
            msg = "connection reset"
            raise OSError(msg)

    assert _web_server.read_json_body({"Content-Length": "2"}, Broken()) is None


def test_a_non_json_post_is_refused_as_cross_origin(served: int) -> None:
    # A cross-site <form> can only send simple content types; refusing them is
    # what forces the browser into a CORS preflight this server never answers.
    status, data = post(served, "/api/mutate/restart", b"{}", ctype="text/plain")
    assert status == 403
    assert json.loads(data)["error"] == "cross-origin request"


def test_a_foreign_host_header_is_refused() -> None:
    headers = {"Host": "rebind.example:8760", "Content-Type": "application/json"}
    assert not _web_server.same_origin(headers, 8760)
    ok = {"Host": "localhost:8760", "Content-Type": "application/json; charset=utf-8"}
    assert _web_server.same_origin(ok, 8760)
    assert not _web_server.same_origin({}, 8760)
