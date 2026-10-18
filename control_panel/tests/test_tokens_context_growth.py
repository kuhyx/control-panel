from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from control_panel.tests import _fixture_detail as fd
from control_panel.tests import _fixture_token_classes as ft
from control_panel.tests import _fixture_tokens as fx
from control_panel.tokens import _api, _context_growth, _context_growth_stats, _db

if TYPE_CHECKING:
    from pathlib import Path

HANDOFF = "/h/.claude/handoff/x.md"


@pytest.fixture
def store(sysroot: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(_api, "_now", lambda: fx.T0 + 2 * fx.DAY)
    path = fx.build(sysroot / "home/tester" / _db.STORE)
    ft.add(
        path,
        turns=[
            ft.turn(ts=fx.T0 + 10, context=100_000, usd=0.5),
            ft.turn(ts=fx.T0 + 20, context=260_000, usd=0.5),
            ft.turn(ts=fx.T0 + 30, context=310_000, usd=1.0),
        ],
        prompts=[
            ("s3", 0, fx.T0 + 5, "p", f"Read {HANDOFF} and continue"),
            ("s9", 0, fx.T0 + 5, "p", "write a handoff"),
            ("s3", 1, fx.T0 + 25, "p", "no hand-off here"),
        ],
    )
    fd.insert(
        path,
        calls=[
            fd.call(key="s3", name="Write", family="Write", target=HANDOFF),
            fd.call(key="s3", name="Write", family="Write", target="/r/a.py"),
        ],
        marks=[fd.mark(key="s3", kind="hook_msg", detail="wrote HANDOFF.md")],
    )
    return path


def _panel(query: str = "") -> dict[str, Any]:
    _, payload = _api.route(["panel", "context_growth"], query)
    return payload


def test_distribution_percentiles_and_histogram(store: Path) -> None:
    payload = _panel()
    assert payload["percentiles"] == {"p50": 100_000, "p90": 400_000, "p99": 400_000}
    calls = {b["bucket"]: b["calls"] for b in payload["histogram"]}
    assert calls == {
        "0-50k": 3,
        "50-100k": 0,
        "100-150k": 1,
        "150-200k": 0,
        "200-250k": 0,
        "250-300k": 1,
        "300k+": 2,
    }


def test_growth_curves_for_the_dearest_sessions(store: Path) -> None:
    growth = _panel()["growth"]
    assert [g["key"] for g in growth] == ["s2", "s1", "s1/agent-a", "s3"]
    assert growth[3]["points"] == [
        {"call": 1, "context": 100_000},
        {"call": 2, "context": 260_000},
        {"call": 3, "context": 310_000},
    ]
    assert growth[1]["title"] == "fix a"


def test_crossings_rank_by_spend_over_300k(store: Path) -> None:
    rows = _panel()["crossings"]
    assert [r["key"] for r in rows] == ["s1", "s3"]
    s3 = rows[1]
    assert (s3["max_context"], s3["calls_over_250k"], s3["calls_over_300k"]) == (
        310_000,
        2,
        1,
    )
    assert s3["usd_over_300k"] == pytest.approx(1.0)
    assert s3["title"] == ""


def test_handoffs_from_writes_prompts_and_marks(store: Path) -> None:
    rows = _panel()["handoffs"]
    assert sorted(r["source"] for r in rows) == ["mark", "prompt", "write"]
    assert {r["key"] for r in rows} == {"s3"}
    assert any(r["detail"] == HANDOFF for r in rows)


@pytest.mark.parametrize(
    ("query", "calls", "handoffs"),
    [
        ("from=2026-09-28&to=2026-09-28", 6, 3),
        ("cwd=/home/tester/src", 6, 3),
        ("model=claude-sonnet-5-5", 1, 0),
        ("scope=main", 6, 3),
        ("scope=sub", 1, 0),
    ],
)
def test_every_filter_applies(
    store: Path, query: str, calls: int, handoffs: int
) -> None:
    payload = _panel(query)
    assert sum(b["calls"] for b in payload["histogram"]) == calls
    assert len(payload["handoffs"]) == handoffs


def test_an_empty_range_has_no_rows(store: Path) -> None:
    payload = _panel("from=2020-01-01&to=2020-01-02")
    assert payload["percentiles"] == {"p50": None, "p90": None, "p99": None}
    assert payload["crossings"] == []
    assert payload["growth"] == []


def test_long_sessions_are_thinned_but_keep_their_last_call() -> None:
    points = _context_growth.thin(list(range(1, 1002)))
    assert len(points) <= _context_growth.MAX_POINTS + 1
    assert points[-1] == {"call": 1001, "context": 1001}
    assert points[0] == {"call": 1, "context": 1}


def test_percentile_is_nearest_rank() -> None:
    assert _context_growth_stats.percentile([3, 1, 2], 0.5) == 2
    assert _context_growth_stats.percentile([], 0.5) is None
