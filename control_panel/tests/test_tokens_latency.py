from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from control_panel.tests import _fixture_detail as fd
from control_panel.tests import _fixture_token_classes as ft
from control_panel.tests import _fixture_tokens as fx
from control_panel.tokens import _api, _db

if TYPE_CHECKING:
    from pathlib import Path

SONNET = "claude-sonnet-5-5"
T0 = fx.T0


@pytest.fixture
def store(sysroot: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(_api, "_now", lambda: T0 + 2 * fx.DAY)
    path = fx.build(sysroot / "home/tester" / _db.STORE)
    away = {"day": "2026-09-29", "cwd": "/home/tester"}
    ft.add(
        path,
        prompts=[
            ("s1", 1, T0 + 100, "p", "and b"),
            ("s1", 2, T0 + 3630, "p", "and c"),
            ("s2", 1, T0 + fx.DAY + 5, "p", "more"),
            ("s7", 1, T0 + 40, "p", "queued while s7 replied"),
        ],
        turns=[ft.turn(key="s7", ts=T0 + 50), ft.turn(key="s8", ts=T0 + 50)],
    )
    fd.insert(
        path,
        turns=[
            fd.turn_detail(key="s3", ts=T0 + 10, latency_s=2.0),
            fd.turn_detail(key="s3", ts=T0 + 20, latency_s=4.0),
            fd.turn_detail(key="s3", ts=T0 + 30, latency_s=0.0),
            fd.turn_detail(key="s1/agent-b", ts=T0 + 40, model=SONNET, latency_s=10.0),
            fd.turn_detail(key="s5", ts=T0 + fx.DAY + 10, latency_s=6.0, **away),
        ],
        calls=[
            fd.call(),
            fd.call(ts=T0 + 5, end_ts=T0 + 15),
            fd.call(name="Read", ts=T0 + 6, end_ts=T0 + 6.5),
            fd.call(ts=T0 + 7, end_ts=T0 + 6),
        ],
    )
    return path


def _panel(query: str = "") -> dict[str, Any]:
    _, payload = _api.route(["panel", "latency"], query)
    return payload


def test_model_latency_per_day_and_model(store: Path) -> None:
    payload = _panel()
    day = payload["daily"][0]
    assert (day["day"], day["calls"], day["p50"], day["p90"]) == (
        "2026-09-28",
        3,
        4.0,
        10.0,
    )
    models = {m["model"]: m for m in payload["models"]}
    assert models["claude-opus-5-5"]["p50"] == 4.0
    assert models[SONNET]["calls"] == 1
    assert "first record" in payload["caption"]


def test_tool_time_per_tool(store: Path) -> None:
    tools = _panel()["tools"]
    assert [t["name"] for t in tools] == ["Bash", "Read"]
    bash = tools[0]
    assert (bash["calls"], bash["p50"], bash["p95"], bash["total_s"]) == (
        2,
        2.0,
        10.0,
        12.0,
    )


def test_think_time_between_reply_and_next_prompt(store: Path) -> None:
    payload = _panel()
    assert payload["think"] == {"prompts": 3, "p50": 30.0, "p90": 100.0}
    counts = {b["bucket"]: b["prompts"] for b in payload["think_histogram"]}
    assert (counts["<10s"], counts["10-30s"], counts["30s-1m"], counts["1-5m"]) == (
        1,
        0,
        1,
        1,
    )


@pytest.mark.parametrize(
    ("query", "calls", "prompts"),
    [
        ("", 4, 3),
        ("from=2026-09-28&to=2026-09-28", 3, 2),
        ("cwd=/home/tester/src", 3, 2),
        ("model=claude-sonnet-5-5", 1, 0),
        ("scope=main", 3, 3),
        ("scope=sub", 1, 0),
    ],
)
def test_every_filter_applies(
    store: Path, query: str, calls: int, prompts: int
) -> None:
    payload = _panel(query)
    assert sum(m["calls"] for m in payload["models"]) == calls
    assert payload["think"]["prompts"] == prompts


def test_an_empty_range_has_no_rows(store: Path) -> None:
    payload = _panel("from=2020-01-01&to=2020-01-02")
    assert payload["daily"] == []
    assert payload["tools"] == []
    assert payload["think"] == {"prompts": 0, "p50": None, "p90": None}
