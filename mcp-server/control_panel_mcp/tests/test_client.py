"""HTTP client: params, errors, the down message."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

import pytest

from control_panel_mcp import _client

if TYPE_CHECKING:
    from control_panel_mcp.tests.conftest import Fake


def test_get_sends_path_and_drops_empty_params(fake: Fake) -> None:
    fake.routes["/api/tokens/panel/x"] = (200, {"ok": 1})
    assert _client.get("/panel/x", {"cwd": "/a b", "model": ""}) == {"ok": 1}
    assert fake.last() == ("/api/tokens/panel/x", {"cwd": "/a b"})


def test_get_without_params(fake: Fake) -> None:
    fake.routes["/api/tokens"] = (200, {"panels": []})
    assert _client.get("") == {"panels": []}
    assert fake.last() == ("/api/tokens", {})


def test_subagent_key_keeps_slash(fake: Fake) -> None:
    fake.routes["/api/tokens/session/a/agent-b"] = (200, {})
    _client.get("/session/a/agent-b")
    assert fake.last()[0] == "/api/tokens/session/a/agent-b"


def test_http_error_carries_api_message(fake: Fake) -> None:
    with pytest.raises(_client.DashboardError) as err:
        _client.get("/panel/zzz")
    assert str(err.value) == "HTTP 404: nope"
    assert _client.is_missing(err.value)


def test_error_without_message(fake: Fake) -> None:
    fake.routes["/api/tokens/x"] = (503, {})
    with pytest.raises(_client.DashboardError, match="HTTP 503: request failed") as e:
        _client.get("/x")
    assert not _client.is_missing(e.value)


def test_non_json_and_non_object(fake: Fake) -> None:
    fake.routes["/api/tokens/a"] = (200, b"<html>")
    fake.routes["/api/tokens/b"] = (200, [1])
    with pytest.raises(_client.DashboardError, match="not JSON"):
        _client.get("/a")
    with pytest.raises(_client.DashboardError, match="JSON object"):
        _client.get("/b")


def test_down_names_the_fix(down: None) -> None:
    with pytest.raises(_client.DashboardError) as err:
        _client.get("/panel/overview")
    assert str(err.value).startswith(_client.DOWN)
    assert err.value.status == 0


def test_base_url_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CONTROL_PANEL_URL", raising=False)
    assert _client.base_url() == _client.DEFAULT_URL


def test_url_without_port_uses_80(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[tuple[str, int]] = []

    class Conn:
        def __init__(self, host: str, port: int, timeout: float) -> None:
            seen.append((host, port))

        def request(self, *_args: object) -> None:
            msg = "refused"
            raise OSError(msg)

        def close(self) -> None:
            return

    monkeypatch.setenv("CONTROL_PANEL_URL", "http://")
    monkeypatch.setattr(_client.http.client, "HTTPConnection", Conn)
    with pytest.raises(_client.DashboardError):
        _client.get("/x")
    assert seen == [("127.0.0.1", 80)]


@pytest.mark.parametrize(
    ("window", "expected"),
    [
        ("", {}),
        ("  ", {}),
        ("7d", {"from": "2026-10-12"}),
        ("1d", {"from": "2026-10-18"}),
        ("2026-10-01..2026-10-07", {"from": "2026-10-01", "to": "2026-10-07"}),
        ("2026-10-01..", {"from": "2026-10-01"}),
        ("2026-10-11-1800", {"window": "2026-10-11-1800"}),
    ],
)
def test_window_params(window: str, expected: dict[str, str]) -> None:
    assert _client.window_params(window, date(2026, 10, 18)) == expected


def test_window_params_defaults_to_today() -> None:
    today = _client.local_today().isoformat()
    assert _client.window_params("1d") == {"from": today}


def test_filter_params_split_shared_and_columns() -> None:
    got = _client.filter_params("?cwd=/x&scope=sub&final_tag==DONE", "sessions")
    assert got == {"cwd": "/x", "scope": "sub", "t.sessions.f.final_tag": "=DONE"}
    assert _client.filter_params("window=2026-10-11-1800", "s") == {
        "window": "2026-10-11-1800"
    }


def test_table_params() -> None:
    assert _client.table_params("sessions", "foo", "-usd", 5) == {
        "t.sessions.q": "foo",
        "t.sessions.sort": "-usd",
        "t.sessions.limit": "5",
    }
    assert _client.table_params("s", "", "", 0) == {}
