from __future__ import annotations

from contextlib import closing
import sqlite3
from typing import TYPE_CHECKING, Any

import pytest

from control_panel.tests import _fixture_detail as fd
from control_panel.tests import _fixture_tokens as fx
from control_panel.tokens import _api, _db
from control_panel.tokens import _registry as registry

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def store(sysroot: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(_api, "_now", lambda: fx.T0 + 2 * fx.DAY)
    path = fx.build(sysroot / "home/tester" / _db.STORE)
    calls = [
        fd.call(result_tokens=10, sig="a", batch=2),
        fd.call(result_tokens=20, sig="a", batch=2, carry_usd=0.5),
        fd.call(result_tokens=30, sig="a", is_error=1, error_kind="exit_code"),
        fd.call(result_tokens=1000, sig="b", is_error=1, error_kind="time_cap"),
        fd.call(
            name="Edit",
            family="Edit:file",
            target="/r/a.py",
            sig="c",
            is_error=1,
            error_kind="rejected",
        ),
        fd.call(
            name="Edit",
            family="Edit:file",
            target="/r/a.py",
            sig="d",
            is_error=1,
            error_kind="denied",
        ),
        fd.call(
            name="Write",
            family="Write:file",
            target="/r/b.py",
            sig="e",
            is_error=1,
            error_kind="hook",
        ),
        fd.call(key="s1/agent-a", model="claude-sonnet-5-5", sig="a"),
        fd.call(
            ts=fx.T0 + fx.DAY, day="2026-09-29", cwd="/home/tester", key="s2", sig="a"
        ),
    ]
    fd.insert(path, calls=calls)
    with closing(sqlite3.connect(path)) as conn:
        conn.executemany(
            "INSERT INTO events VALUES (?,?,?,?)",
            [
                ("time-cap", fx.T0, "killed_foreground", "sleep 999"),
                ("time-cap", fx.T0 + 5, "killed_background", "make"),
                ("time-cap", fx.T0 + 9, "denied", "nohup x &"),
                ("time-cap", fx.T0 + 9, "unmatched", "y"),
                ("task-size-miss", fx.T0, "resumed", "z"),
                ("time-cap", fx.T0 - 90 * fx.DAY, "killed_foreground", "old"),
            ],
        )
        conn.commit()
    return path


def _tools(query: str = "") -> dict[str, Any]:
    _, payload = _api.route(["panel", "tools"], query)
    return payload


def _by(rows: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    return {r[key]: r for r in rows}


def test_per_tool_calls_errors_and_result_percentiles(store: Path) -> None:
    payload = _tools()
    bash = _by(payload["tools"], "name")["Bash"]
    assert (bash["calls"], bash["errors"]) == (6, 2)
    assert bash["error_rate"] == pytest.approx(2 / 6)
    assert (bash["result_p50"], bash["result_p95"]) == (30, 1000)
    assert bash["time_cap"] == 1
    edit = _by(payload["tools"], "name")["Edit"]
    assert (edit["rejected"], edit["denied"], edit["hook"]) == (1, 1, 0)
    assert payload["tools"][0]["name"] == "Bash"
    family = _by(payload["families"], "family")["Write:file"]
    assert (family["calls"], family["hook"], family["error_rate"]) == (1, 1, 1.0)
    assert "p95" in payload["caption"]


def test_totals_and_time_cap_events(store: Path) -> None:
    totals = _tools()["totals"]
    assert totals["calls"] == 9
    assert totals["errors"] == 5
    assert totals["failed"] == {"rejected": 1, "denied": 1, "hook": 1}
    assert totals["time_cap_calls"] == 1
    assert totals["time_cap_events"] == {"killed": 2, "denied": 1, "unmatched": 1}
    assert totals["batched_share"] == pytest.approx(2 / 9)


def test_time_cap_table_lists_kills_by_day_and_kind(store: Path) -> None:
    rows = _tools()["time_cap"]
    assert [(r["kind"], r["count"]) for r in rows] == [
        ("denied", 1),
        ("killed_background", 1),
        ("killed_foreground", 1),
        ("unmatched", 1),
    ]
    assert rows[0]["day"] == "2026-09-28"


def test_loops_are_identical_calls_repeated_more_than_twice(store: Path) -> None:
    loops = _tools()["loops"]
    assert len(loops) == 1
    loop = loops[0]
    assert (loop["key"], loop["name"], loop["target"], loop["repeats"]) == (
        "s1",
        "Bash",
        "git status",
        3,
    )
    assert loop["cost_usd"] == pytest.approx(0.1 + 0.5 + 0.1 + 0.03)


def test_batching_rate_per_day(store: Path) -> None:
    second, first = _tools()["batching"]
    assert (first["day"], first["calls"], first["batched"]) == ("2026-09-28", 8, 2)
    assert first["share"] == pytest.approx(0.25)
    assert (second["day"], second["share"]) == ("2026-09-29", 0.0)


@pytest.mark.parametrize(
    ("query", "count", "events"),
    [
        ("cwd=/home/tester/src", 8, False),
        ("model=claude-sonnet-5-5", 1, False),
        ("scope=main", 8, False),
        ("scope=sub", 1, False),
        ("from=2026-09-29&to=2026-09-29", 1, True),
    ],
)
def test_every_filter_applies(
    store: Path, query: str, count: int, *, events: bool
) -> None:
    payload = _tools(query)
    assert payload["totals"]["calls"] == count
    assert sum(r["calls"] for r in payload["tools"]) == count
    assert (payload["totals"]["time_cap_events"] is not None) is events
    assert bool(payload["time_cap"]) is False


def test_an_empty_range_has_no_rows(store: Path) -> None:
    payload = _tools("from=2020-01-01&to=2020-01-02")
    assert payload["tools"] == []
    assert payload["loops"] == []
    assert payload["batching"] == []
    assert payload["totals"]["batched_share"] is None
    assert payload["totals"]["error_rate"] is None


def test_the_batching_chart_list_is_never_cut(store: Path) -> None:
    payload = _tools("t.tools.limit=1")
    assert payload["_tables"]["batching"]["shown"] == len(payload["batching"]) == 2
    assert registry.PANELS["tools"].tables == {
        **{t: {"limit": "25"} for t in ("tools", "families", "loops", "time_cap")},
        "batching": {"limit": "0"},
    }
