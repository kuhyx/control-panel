from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from control_panel.tests import _fixture_prompt_cost as fpc
from control_panel.tests import _fixture_tokens as fx
from control_panel.tokens import _api, _db

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def store(sysroot: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(_api, "_now", lambda: fx.T0 + 2 * fx.DAY)
    path = fx.build(sysroot / "home/tester" / _db.STORE)
    fpc.prompts(
        path,
        [
            ("s1", 2, fx.T0 + 7200, "and c", 0.05, 0.0),
            ("s2", 0, fx.T0 + fx.DAY, "ask", 4.0, 0.0),
            ("s7", 0, fx.T0, "no calls stored", 9.0, 0.0),
        ],
    )
    return path


def _prompts(query: str = "") -> dict[str, Any]:
    _, payload = _api.route(["panel", "prompts"], query)
    return payload


def _keys(payload: dict[str, Any]) -> list[tuple[str, int]]:
    return [(r["key"], r["idx"]) for r in payload["prompts"]]


def test_costliest_prompts_first_with_both_sides(store: Path) -> None:
    payload = _prompts()
    assert _keys(payload) == [("s1", 0), ("s2", 0), ("s1", 1), ("s1", 2)]
    first = payload["prompts"][0]
    assert (first["usd_own"], first["usd_sub"]) == (2.0, 3.0)
    assert (first["usd"], first["total"]) == (5.0, 5.0)
    assert (first["text"], first["active_s"], first["calls"]) == ("fix a", 600, 1)
    assert first["ts"] == fx.T0
    assert "usd_own" in payload["caption"]


def test_daily_median_and_mean(store: Path) -> None:
    daily = _prompts()["daily"]
    assert [d["day"] for d in daily] == ["2026-09-28", "2026-09-29"]
    first = daily[0]
    assert first["prompts"] == 3
    assert first["median_usd"] == pytest.approx(1.0)
    assert first["mean_usd"] == pytest.approx(6.05 / 3)
    assert first["usd"] == pytest.approx(6.05)


def test_histogram_buckets_every_prompt(store: Path) -> None:
    buckets = {b["bucket"]: b["prompts"] for b in _prompts()["histogram"]}
    assert len(buckets) == 8
    assert buckets["< $0.10"] == 1
    assert buckets["$1-2"] == 1
    assert buckets["$2-5"] == 1
    assert buckets["$5-10"] == 1
    assert buckets["≥ $20"] == 0


def test_totals(store: Path) -> None:
    totals = _prompts()["totals"]
    assert totals["prompts"] == 4
    assert totals["usd"] == pytest.approx(10.05)
    assert totals["median_usd"] == pytest.approx(2.5)
    assert totals["mean_usd"] == pytest.approx(10.05 / 4)
    assert totals["top10_share"] == pytest.approx(1.0)


@pytest.mark.parametrize(
    ("query", "keys"),
    [
        ("scope=main", [("s2", 0), ("s1", 0), ("s1", 1), ("s1", 2)]),
        ("scope=sub", [("s1", 0)]),
        ("model=claude-sonnet-5-5", [("s1", 0), ("s1", 1), ("s1", 2)]),
        ("cwd=/home/tester/src", [("s1", 0), ("s1", 1), ("s1", 2)]),
        ("from=2026-09-29", [("s2", 0)]),
    ],
)
def test_every_filter_applies(
    store: Path, query: str, keys: list[tuple[str, int]]
) -> None:
    assert _keys(_prompts(query)) == keys


def test_scope_picks_the_cost_side(store: Path) -> None:
    assert _prompts("scope=main")["prompts"][1]["usd"] == 2.0
    sub = _prompts("scope=sub")["prompts"][0]
    assert (sub["usd"], sub["total"]) == (3.0, 5.0)


def test_tables_take_the_shared_params(store: Path) -> None:
    payload = _prompts("t.prompts.limit=1")
    assert _keys(payload) == [("s1", 0)]
    assert payload["_tables"]["prompts"]["total"] == 4


def test_an_empty_range_has_no_rows(store: Path) -> None:
    payload = _prompts("from=2020-01-01&to=2020-01-02")
    assert payload["prompts"] == []
    assert payload["daily"] == []
    totals = payload["totals"]
    assert totals["prompts"] == 0
    assert totals["median_usd"] is None
    assert totals["mean_usd"] is None
    assert totals["top10_share"] is None
