from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from control_panel.tests import _fixture_estimator as fe
from control_panel.tests import _fixture_tokens as fx
from control_panel.tokens import _api, _db

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def store(sysroot: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(_api, "_now", lambda: fx.T0 + 2 * fx.DAY)
    path = fx.build(sysroot / "home/tester" / _db.STORE)
    fe.estimates(path, [("s1", 1), ("s2", 4), ("s3", 0), ("s9", 5)])
    fe.turn(path, "s3", fx.T0 + 7200)
    fe.events(
        path,
        [
            ("task-size-miss", fx.T0, "split-ignored", "Implement x"),
            ("task-size-miss", fx.T0 + 60, "split-ignored", "Implement y"),
            ("task-size-miss", fx.T0 + fx.DAY, "predicted-fits", "fix z"),
            ("time-cap", fx.T0, "killed_foreground", "pytest"),
        ],
    )
    return path


def _estimator(query: str = "") -> dict[str, Any]:
    _, payload = _api.route(["panel", "estimator"], query)
    return payload


def _actual(payload: dict[str, Any]) -> dict[str, tuple[int, str]]:
    return {
        r["session_id"]: (r["actual_calls"], r["miss"]) for r in payload["sessions"]
    }


def test_sessions_compare_the_estimate_with_actual_calls(store: Path) -> None:
    payload = _estimator()
    rows = payload["sessions"]
    assert [r["session_id"] for r in rows] == ["s3", "s2", "s1"]
    s3, s2, s1 = rows
    assert (s3["est_calls"], s3["actual_calls"], s3["ratio"]) == (0, 1, None)
    assert s3["miss"] == "over"
    assert (s2["ratio"], s2["miss"]) == (0.25, "under")
    assert (s1["ratio"], s1["miss"], s1["title"]) == (3.0, "over", "fix a")
    assert s1["usd"] == pytest.approx(6.0)
    assert s1["cwd"] == "/home/tester/src/a"
    assert s3["title"] == ""
    assert "2x" in payload["caption"]


def test_tiles_summarise_the_misses(store: Path) -> None:
    totals = _estimator()["totals"]
    assert totals["sessions"] == 3
    assert totals["within_share"] == 0.0
    assert totals["over_share"] == pytest.approx(2 / 3)
    assert totals["under_share"] == pytest.approx(1 / 3)
    assert totals["median_ratio"] == pytest.approx(1.625)
    assert totals["gate_misses"] == 3
    assert totals["predicted_fits"] == 1


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("scope=main", {"s1": (2, ""), "s2": (1, "under"), "s3": (1, "over")}),
        ("scope=sub", {"s1": (1, "")}),
        ("model=claude-sonnet-5-5", {"s1": (1, "")}),
        ("cwd=/home/tester/src", {"s1": (3, "over"), "s3": (1, "over")}),
        ("from=2026-09-29", {"s2": (1, "under")}),
    ],
)
def test_every_filter_narrows_the_actual_calls(
    store: Path, query: str, expected: dict[str, tuple[int, str]]
) -> None:
    assert _actual(_estimator(query)) == expected


def test_events_per_day_and_kind_take_the_date_range_only(store: Path) -> None:
    payload = _estimator()
    assert [(r["day"], r["kind"], r["count"]) for r in payload["events"]] == [
        ("2026-09-29", "predicted-fits", 1),
        ("2026-09-28", "split-ignored", 2),
    ]
    assert payload["events"][1]["example"] == "Implement y"
    assert payload["events_daily"] == [
        {"day": "2026-09-28", "count": 2},
        {"day": "2026-09-29", "count": 1},
    ]
    assert _estimator("cwd=/nowhere&scope=sub")["events"] == payload["events"]
    assert _estimator("from=2026-09-29")["totals"]["gate_misses"] == 1
    assert "date range" in payload["filtered_by"]


def test_an_empty_range_has_no_rows(store: Path) -> None:
    payload = _estimator("from=2020-01-01&to=2020-01-02")
    assert payload["sessions"] == []
    assert payload["events"] == []
    totals = payload["totals"]
    assert totals["sessions"] == 0
    assert totals["within_share"] is None
    assert totals["median_ratio"] is None
