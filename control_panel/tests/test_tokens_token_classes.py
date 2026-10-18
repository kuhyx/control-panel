from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from control_panel.tests import _fixture_detail as fd
from control_panel.tests import _fixture_token_classes as ft
from control_panel.tests import _fixture_tokens as fx
from control_panel.tokens import _api, _db, _token_classes_prices

if TYPE_CHECKING:
    from pathlib import Path

SONNET = "claude-sonnet-5-5"
UNTIL = fx.T0 + 2 * fx.DAY


@pytest.fixture
def store(sysroot: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(_api, "_now", lambda: UNTIL)
    path = fx.build(sysroot / "home/tester" / _db.STORE)
    t1, t2, t3 = fx.T0 + 100, fx.T0 + 200, fx.T0 + 4200
    t5, t6 = fx.T0 + fx.DAY + 100, UNTIL - 60
    ft.add(
        path,
        turns=[
            ft.turn(ts=t1, input=1000, cache_write=10000, output=500, usd=0.5),
            ft.turn(ts=t2, cache_write=1000, cache_read=50000, output=100, usd=0.1),
            ft.turn(ts=t3, cache_read=51000, output=10, usd=0.02),
            ft.turn(key="s1/agent-b", ts=fx.T0 + 300, model=SONNET, input=7),
            ft.turn(
                key="s5",
                ts=t5,
                day="2026-09-29",
                cwd="/home/tester",
                input=30,
                cache_write=500,
                usd=0.2,
            ),
            ft.turn(key="s6", ts=t6, day="2026-09-30", cache_write=800, usd=0.3),
        ],
    )
    fd.insert(
        path,
        turns=[
            fd.turn_detail(key="s3", ts=t1, cw_1h=6000, cw_5m=2000),
            fd.turn_detail(key="s3", ts=t2, cw_1h=1000, cw_5m=0),
            fd.turn_detail(key="s3", ts=t3, cw_1h=0, cw_5m=0),
            fd.turn_detail(
                key="s1/agent-b", ts=fx.T0 + 300, model=SONNET, cw_1h=0, cw_5m=0
            ),
            fd.turn_detail(
                key="s5",
                ts=t5,
                day="2026-09-29",
                cwd="/home/tester",
                cw_1h=0,
                cw_5m=500,
            ),
            fd.turn_detail(key="s6", ts=t6, day="2026-09-30", cw_1h=800, cw_5m=0),
        ],
        marks=[
            fd.mark(
                kind="compaction",
                name="auto",
                detail="",
                count=2,
                tokens=100_000,
                extra=20_000,
                duration_ms=30_000,
            )
        ],
    )
    return path


def _panel(query: str = "") -> dict[str, Any]:
    _, payload = _api.route(["panel", "token_classes"], query)
    return payload


def test_daily_classes_prices_and_hit_ratio(store: Path) -> None:
    day = _panel()["daily"][0]
    assert day["day"] == "2026-09-28"
    assert (day["input"], day["cw_5m"], day["cw_1h"]) == (1007, 2000, 7000)
    assert (day["unsplit"], day["cache_read"], day["output"]) == (2000, 101000, 610)
    assert day["input_usd"] == pytest.approx(0.004014)
    assert day["cw_1h_usd"] == pytest.approx(0.056)
    assert day["unsplit_usd"] == pytest.approx(0.01)
    assert day["usd"] == pytest.approx(0.112414)
    assert day["hit_ratio"] == pytest.approx(101000 / 113007)


def test_waste_cold_starts_and_pending_writes(store: Path) -> None:
    payload = _panel()
    totals = payload["totals"]
    assert totals["waste_tokens"] == 1500
    assert totals["waste_usd"] == pytest.approx(0.0105)
    assert totals["pending_tokens"] == 800
    assert (totals["cold_starts"], totals["cold_start_usd"]) == (3, pytest.approx(1.0))
    first = payload["waste"][0]
    assert (first["key"], first["wasted_tokens"], first["wasted_calls"]) == (
        "s3",
        1000,
        1,
    )
    assert "1 h" in payload["caption"]


def test_compactions_are_estimated(store: Path) -> None:
    payload = _panel()
    row = payload["compactions"][0]
    assert (row["count"], row["pre_tokens"], row["post_tokens"]) == (2, 100_000, 20_000)
    assert row["duration_s"] == pytest.approx(30.0)
    assert row["est_usd"] == pytest.approx(0.42)
    assert payload["totals"]["compactions"] == 2
    assert payload["totals"]["compaction_usd"] == pytest.approx(0.42)


@pytest.mark.parametrize(
    ("query", "tokens"),
    [
        ("", 1037),
        ("from=2026-09-28&to=2026-09-28", 1007),
        ("cwd=/home/tester/src", 1007),
        ("model=claude-sonnet-5-5", 7),
        ("scope=main", 1030),
        ("scope=sub", 7),
    ],
)
def test_every_filter_applies(store: Path, query: str, tokens: int) -> None:
    assert _panel(query)["totals"]["input"] == tokens


def test_an_empty_range_has_no_rows(store: Path) -> None:
    payload = _panel("from=2020-01-01&to=2020-01-02")
    assert payload["daily"] == []
    assert payload["waste"] == []
    assert payload["totals"]["hit_ratio"] is None


def test_prices_match_the_audit_table() -> None:
    book = _token_classes_prices.BOOK
    assert book.price("claude-haiku-4-5-20251001").output == 5.0
    assert book.price("unknown-model").input == 4.0
    assert book.price("claude-opus-5-5").write_1h == pytest.approx(8.0)
