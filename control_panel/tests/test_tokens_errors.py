from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from control_panel.tests import _fixture_detail as fd
from control_panel.tests import _fixture_tokens as fx
from control_panel.tokens import _api, _db

if TYPE_CHECKING:
    from pathlib import Path

DAY2 = {"ts": fx.T0 + fx.DAY, "day": "2026-09-29", "cwd": "/home/tester"}
SUB = {"key": "s1/agent-a", "model": "claude-sonnet-5-5"}


@pytest.fixture
def store(sysroot: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(_api, "_now", lambda: fx.T0 + 2 * fx.DAY)
    path = fx.build(sysroot / "home/tester" / _db.STORE)
    calls = [
        fd.call(),
        fd.call(ts=fx.T0 + 10, is_error=1, error_kind="exit_code"),
        fd.call(
            ts=fx.T0 + 20,
            name="Read",
            family="Read:file",
            target="/r/a.py",
            is_error=1,
            error_kind="tool_error",
        ),
        fd.call(name="Read", family="Read:file", target="/r/b.py"),
        fd.call(**SUB, ts=fx.T0 + 30, is_error=1, error_kind="denied"),
        fd.call(**DAY2, key="s2", is_error=1, error_kind="exit_code"),
    ]
    marks = [
        fd.mark(),
        fd.mark(kind="api_error", name="rate_limit", detail="usage_limit", count=2),
        fd.mark(
            kind="api_error", name="rate_limit", detail="resets 8pm", ts=fx.T0 + 50
        ),
        fd.mark(**SUB, kind="api_error", name="overloaded", detail="Overloaded"),
        fd.mark(kind="interrupt", name="user", detail=""),
        fd.mark(**DAY2, key="s2", kind="interrupt", name="user", detail="", count=3),
        fd.mark(**DAY2, key="s2", kind="api_error", name="rate_limit", detail="x"),
    ]
    fd.insert(path, calls=calls, marks=marks)
    return path


def _errors(query: str = "") -> dict[str, Any]:
    _, payload = _api.route(["panel", "errors"], query)
    return payload


def test_api_errors_per_type_and_detail(store: Path) -> None:
    payload = _errors()
    types = payload["api_error_types"]
    assert [(r["type"], r["count"], r["sessions"]) for r in types] == [
        ("rate_limit", 4, 2),
        ("overloaded", 1, 1),
    ]
    assert types[0]["last_ts"] == fx.T0 + fx.DAY
    detail = payload["api_errors"]
    assert (detail[0]["type"], detail[0]["detail"], detail[0]["count"]) == (
        "rate_limit",
        "usage_limit",
        2,
    )
    assert len(detail) == 4
    assert "rate_limit" in payload["caption"]


def test_tool_errors_by_kind_and_tool_with_rates(store: Path) -> None:
    payload = _errors()
    kinds = payload["error_kinds"]
    assert [(r["error_kind"], r["count"]) for r in kinds] == [
        ("exit_code", 2),
        ("denied", 1),
        ("tool_error", 1),
    ]
    assert kinds[0]["share"] == pytest.approx(0.5)
    assert kinds[0]["rate"] == pytest.approx(2 / 6)
    tools = payload["error_tools"]
    assert [(r["name"], r["family"], r["calls"], r["errors"]) for r in tools] == [
        ("Bash", "git status", 4, 3),
        ("Read", "Read:file", 2, 1),
    ]
    assert tools[0]["error_rate"] == pytest.approx(0.75)


def test_recent_failing_calls_newest_first(store: Path) -> None:
    recent = _errors()["recent"]
    assert [r["error_kind"] for r in recent] == [
        "exit_code",
        "denied",
        "tool_error",
        "exit_code",
    ]
    first = recent[0]
    assert (first["key"], first["name"], first["family"]) == (
        "s2",
        "Bash",
        "git status",
    )
    assert first["target"] == "git status"
    assert first["ts"] == fx.T0 + fx.DAY


def test_daily_series_and_tiles(store: Path) -> None:
    payload = _errors()
    first, second = payload["daily"]
    assert first == {
        "day": "2026-09-28",
        "api_errors": 4,
        "rate_limits": 3,
        "interrupts": 1,
        "calls": 5,
        "tool_errors": 3,
        "error_rate": pytest.approx(0.6),
    }
    assert (second["interrupts"], second["calls"], second["api_errors"]) == (3, 1, 1)
    totals = payload["totals"]
    assert totals["api_errors"] == 5
    assert totals["rate_limit_hits"] == 4
    assert totals["rate_limit_sessions"] == 2
    assert totals["last_rate_limit_ts"] == fx.T0 + fx.DAY
    assert totals["interrupts"] == 4
    assert (totals["calls"], totals["tool_errors"]) == (6, 4)
    assert totals["error_rate"] == pytest.approx(4 / 6)


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("cwd=/home/tester/src", (5, 3, 4, 1)),
        ("model=claude-sonnet-5-5", (1, 1, 1, 0)),
        ("scope=main", (5, 3, 4, 4)),
        ("scope=sub", (1, 1, 1, 0)),
        ("from=2026-09-29&to=2026-09-29", (1, 1, 1, 3)),
    ],
)
def test_every_filter_applies(
    store: Path, query: str, expected: tuple[int, int, int, int]
) -> None:
    totals = _errors(query)["totals"]
    keys = ("calls", "tool_errors", "api_errors", "interrupts")
    assert tuple(totals[k] for k in keys) == expected


def test_an_empty_range_has_no_rows(store: Path) -> None:
    payload = _errors("from=2020-01-01&to=2020-01-02")
    assert payload["recent"] == []
    assert payload["daily"] == []
    assert payload["api_error_types"] == []
    totals = payload["totals"]
    assert (totals["calls"], totals["error_rate"], totals["last_rate_limit_ts"]) == (
        0,
        None,
        None,
    )


def test_tables_take_the_shared_params(store: Path) -> None:
    payload = _errors("t.recent.limit=1")
    assert len(payload["recent"]) == 1
    assert payload["_tables"]["recent"]["total"] == 4
