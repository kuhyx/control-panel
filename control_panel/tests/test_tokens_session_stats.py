from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from control_panel.tests import _fixture_detail as fd
from control_panel.tests import _fixture_subagents as fs
from control_panel.tests import _fixture_tokens as fx
from control_panel.tokens import _api, _db
from control_panel.tokens import _registry as registry

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def store(sysroot: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(_api, "_now", lambda: fx.T0 + 2 * fx.DAY)
    path = fx.build(sysroot / "home/tester" / _db.STORE)
    fs.insert(
        path,
        turns=[fs.turn("s3", fx.T0 + 120, 0.25)],
        prompts=[
            ("s1", 0, fx.T0, "p0", "fix a"),
            ("s1", 1, fx.T0 + 3600, "p1", "and b"),
            ("s2", 0, fx.T0 + fx.DAY, "p2", "ask"),
        ],
    )
    fd.insert(path, marks=[fd.mark(kind="interrupt", name="user", count=2)])
    return path


def _stats(query: str = "") -> dict[str, Any]:
    _, payload = _api.route(["panel", "session_stats"], query)
    return payload


def _hist(rows: list[dict[str, Any]]) -> dict[str, int]:
    return {r["bucket"]: r["sessions"] for r in rows if r["sessions"]}


def test_cost_histogram_buckets_sessions_by_usd(store: Path) -> None:
    payload = _stats()
    assert _hist(payload["cost_hist"]) == {"<$0.50": 1, "$2-5": 1, "$5-10": 1}
    assert payload["totals"]["sessions"] == 3
    assert payload["totals"]["usd_per_session"] == pytest.approx(10.25 / 3)
    assert "position" in payload["caption"]


def test_cost_by_call_position(store: Path) -> None:
    rows = {r["bucket"]: r for r in _stats()["position"] if r["calls"]}
    assert rows["1"]["mean_usd"] == pytest.approx((2 + 3 + 4 + 0.25) / 4)
    assert (rows["2-5"]["calls"], rows["2-5"]["mean_usd"]) == (1, 1.0)
    assert set(rows) == {"1", "2-5"}


def test_prompts_and_interruptions_per_session(store: Path) -> None:
    payload = _stats()
    assert _hist(payload["prompts_hist"]) == {"0": 1, "1": 1, "2": 1}
    assert _hist(payload["interrupts_hist"]) == {"0": 2, "2": 1}
    assert payload["totals"]["interrupts"] == 2


def test_daily_sessions_and_concurrency(store: Path) -> None:
    first, second = _stats()["daily"]
    assert (first["day"], first["sessions"], first["max_concurrent"]) == (
        "2026-09-28",
        2,
        2,
    )
    assert (second["day"], second["sessions"], second["max_concurrent"]) == (
        "2026-09-29",
        1,
        1,
    )


def test_position_counts_before_the_filter(store: Path) -> None:
    rows = {r["bucket"]: r for r in _stats("cwd=/home/tester/src")["position"]}
    assert rows["2-5"]["calls"] == 1
    sonnet = {
        r["bucket"]: r["calls"]
        for r in _stats("model=claude-sonnet-5-5")["position"]
        if r["calls"]
    }
    assert sonnet == {"1": 1}


@pytest.mark.parametrize(
    ("query", "sessions"),
    [
        ("cwd=/home/tester/src", 2),
        ("model=claude-sonnet-5-5", 1),
        ("scope=main", 3),
        ("scope=sub", 1),
        ("from=2026-09-29&to=2026-09-29", 1),
    ],
)
def test_every_filter_applies(store: Path, query: str, sessions: int) -> None:
    assert _stats(query)["totals"]["sessions"] == sessions


def test_an_empty_range_has_no_rows(store: Path) -> None:
    payload = _stats("from=2020-01-01&to=2020-01-02")
    assert payload["daily"] == []
    assert _hist(payload["cost_hist"]) == {}
    assert payload["totals"]["usd_per_session"] is None


def test_the_daily_chart_list_is_never_cut() -> None:
    assert registry.PANELS["session_stats"].tables == {
        "daily": {"limit": "0"},
        "position": {"limit": "0"},
    }
