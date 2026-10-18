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
T5 = fx.T0 + fx.DAY + 10


@pytest.fixture
def store(sysroot: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(_api, "_now", lambda: fx.T0 + 2 * fx.DAY)
    path = fx.build(sysroot / "home/tester" / _db.STORE)
    away = {"day": "2026-09-29", "cwd": "/home/tester"}
    ft.add(
        path,
        turns=[
            ft.turn(ts=fx.T0 + 10, output=1000, usd=0.1),
            ft.turn(ts=fx.T0 + 20, output=200, usd=0.05),
            ft.turn(key="s1/agent-b", ts=fx.T0 + 30, model=SONNET, output=50, usd=0.01),
            ft.turn(key="s5", ts=T5, output=10, usd=0.2, **away),
        ],
    )
    fd.insert(
        path,
        turns=[
            fd.turn_detail(
                key="s3", ts=fx.T0 + 10, out_think=600, out_text=300, out_tool=100
            ),
            fd.turn_detail(
                key="s3", ts=fx.T0 + 20, out_think=0, out_text=200, out_tool=0
            ),
            fd.turn_detail(
                key="s1/agent-b",
                ts=fx.T0 + 30,
                model=SONNET,
                out_think=0,
                out_text=50,
                out_tool=0,
            ),
            fd.turn_detail(
                key="s5", ts=T5, out_think=0, out_text=10, out_tool=0, **away
            ),
        ],
    )
    return path


def _panel(query: str = "") -> dict[str, Any]:
    _, payload = _api.route(["panel", "output"], query)
    return payload


def test_daily_split_and_output_share(store: Path) -> None:
    day = _panel()["daily"][0]
    assert day["day"] == "2026-09-28"
    assert (day["think"], day["text"], day["tool"]) == (600, 550, 100)
    assert day["output"] == 1250
    assert day["output_usd"] == pytest.approx(0.0245)
    assert day["spend_usd"] == pytest.approx(6.16)
    assert day["output_share"] == pytest.approx(0.0245 / 6.16)


def test_totals_and_longest_replies(store: Path) -> None:
    payload = _panel()
    totals = payload["totals"]
    assert totals["output_usd"] == pytest.approx(0.0247)
    assert totals["spend_usd"] == pytest.approx(10.36)
    first = payload["longest"][0]
    assert (first["key"], first["output"], first["think"]) == ("s3", 1000, 600)
    assert first["output_usd"] == pytest.approx(0.02)
    assert "estimate" in payload["caption"]


def test_a_reply_without_detail_has_no_split(store: Path) -> None:
    rows = _panel("t.longest.limit=0")["longest"]
    bare = [r for r in rows if r["key"] == "s1" and r["output"] == 0]
    assert bare
    assert bare[0]["think"] is None


@pytest.mark.parametrize(
    ("query", "tokens"),
    [
        ("", 1260),
        ("from=2026-09-28&to=2026-09-28", 1250),
        ("cwd=/home/tester/src", 1250),
        ("model=claude-sonnet-5-5", 50),
        ("scope=main", 1210),
        ("scope=sub", 50),
    ],
)
def test_every_filter_applies(store: Path, query: str, tokens: int) -> None:
    payload = _panel(query)
    assert payload["totals"]["output"] == tokens
    assert sum(d["think"] + d["text"] + d["tool"] for d in payload["daily"]) == tokens


def test_an_empty_range_has_no_rows(store: Path) -> None:
    payload = _panel("from=2020-01-01&to=2020-01-02")
    assert payload["daily"] == []
    assert payload["longest"] == []
    assert payload["totals"]["output_share"] is None
