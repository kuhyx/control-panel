"""Efficiency and A/B honour cwd / model / scope (computed live)."""

from __future__ import annotations

from contextlib import closing
import sqlite3
from typing import TYPE_CHECKING, Any

import pytest

from control_panel.tests import _fixture_tokens as fx
from control_panel.tokens import _ab_rows, _ab_stats, _api, _db

if TYPE_CHECKING:
    from pathlib import Path

NOW = fx.T0 + 2 * fx.DAY
AB_ROWS = """
CREATE TABLE ab_rows(tool_use_id TEXT PRIMARY KEY, arm TEXT, key TEXT,
    main_key TEXT, is_sub INT, cwd TEXT, model TEXT, ts REAL, usd REAL,
    duration_s REAL, redo INT, followup INT, error INT, correction INT, tag TEXT);
"""


@pytest.fixture
def store(sysroot: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(_api, "_now", lambda: NOW)
    path = fx.build(sysroot / "home/tester" / _db.STORE)
    with closing(sqlite3.connect(path)) as conn:
        conn.executemany(
            "INSERT INTO session_commits VALUES (?,?,?,?,?)",
            [
                ("a1", "/r", fx.T0, "s1", 0),
                ("a2", "/r", fx.T0, "s1", 0),
                ("a3", "/r", fx.T0 - 30 * fx.DAY, "s1", 0),
                ("a4", "/r", NOW - fx.DAY, "s1/agent-a", 0),
                ("b1", "/r", fx.T0, "s2", 0),
            ],
        )
        conn.executemany(
            "INSERT INTO commit_verdicts VALUES (?,?,?,?,?,?)",
            [("a1", "/r", 0, 1, 1, "survived"), ("a2", "/r", 0, 1, 0, "churned")],
        )
        conn.execute("INSERT INTO estimates VALUES ('s1', 10)")
        conn.commit()
    return path


def _panel(name: str, query: str = "") -> dict[str, Any]:
    _, payload = _api.route(["panel", name], query)
    return payload


def test_efficiency_counts_each_sessions_filtered_spend(store: Path) -> None:
    payload = _panel("efficiency")
    (week,) = payload["done"]
    assert (week["week"], week["done"], week["untagged"]) == ("2026-09-28", 1, 1)
    assert week["usd_per_done"] == pytest.approx(6.0)  # s1 incl. its subagent
    (commits,) = [w for w in payload["commits"] if w["week"] == "2026-09-28"]
    assert (commits["survived"], commits["lost"], commits["pending"]) == (1, 1, 2)
    assert commits["usd_per_survivor"] == pytest.approx(10.0)
    old = next(w for w in payload["commits"] if w["week"] != "2026-09-28")
    assert old["unknown"] == 1
    (estimate,) = payload["estimate"]
    assert estimate["usd_per_unit"] == pytest.approx(0.6)
    assert "cwd" in payload["filtered_by"]


def test_efficiency_scope_and_model_change_the_spend(store: Path) -> None:
    main = _panel("efficiency", "scope=main")["done"][0]
    assert main["usd_per_done"] == pytest.approx(3.0)
    sonnet = _panel("efficiency", "model=claude-sonnet-5-5")
    assert sonnet["done"][0]["usd_per_done"] == pytest.approx(3.0)
    assert sonnet["done"][0]["untagged"] == 0
    assert _panel("efficiency", "cwd=/nowhere")["done"] == []


def test_ab_is_all_time_unless_scoped(store: Path) -> None:
    assert _panel("ab")["filtered_by"] == "all time, all assignments"
    # An older store has no per-assignment rows: the stored summary is served.
    assert _panel("ab", "cwd=/x")["arms"] == fx.AB["arms"]


def test_ab_recounts_arms_for_cwd_model_scope(store: Path) -> None:
    with closing(sqlite3.connect(store)) as conn:
        conn.executescript(AB_ROWS)
        conn.executemany(
            "INSERT INTO ab_rows VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [
                (
                    "t1",
                    "sonnet",
                    "s1",
                    "s1",
                    0,
                    "/home/tester/src/a",
                    "m",
                    0,
                    1.0,
                    60,
                    1,
                    0,
                    0,
                    0,
                    "DONE",
                ),
                (
                    "t2",
                    "sonnet",
                    "s1",
                    "s1",
                    0,
                    "/home/tester/src/a",
                    "m",
                    0,
                    3.0,
                    30,
                    0,
                    1,
                    0,
                    1,
                    "DONE",
                ),
                (
                    "t3",
                    "opus",
                    "s2",
                    "s2",
                    0,
                    "/home/tester",
                    "m",
                    0,
                    2.0,
                    20,
                    0,
                    0,
                    1,
                    0,
                    "untagged",
                ),
            ],
        )
        conn.commit()
    payload = _panel("ab", "cwd=/home/tester/src")
    sonnet, opus = payload["arms"]["sonnet"], payload["arms"]["opus"]
    assert (sonnet["n"], opus["n"]) == (2, 0)
    assert sonnet["redo"]["k"] == 1
    assert sonnet["usd"]["mean"] == pytest.approx(2.0)
    assert sonnet["tags"] == {"DONE": 2}
    assert payload["diffs"]["redo"]["diff"] == pytest.approx(0.5)
    assert payload["banner"] == fx.AB["banner"]
    assert "recounted" in payload["filtered_by"]
    assert _panel("ab", "scope=sub")["arms"]["opus"]["n"] == 0


def test_ab_statistics_match_reference_values() -> None:
    low, high = _ab_stats.wilson(5, 10)
    assert (round(low, 4), round(high, 4)) == (0.2366, 0.7634)
    assert _ab_stats.wilson(0, 0) == (0.0, 1.0)
    assert _ab_stats.mean_ci([]) == {"mean": 0.0, "low": 0.0, "high": 0.0}
    assert _ab_stats.mean_ci([2.0])["low"] == pytest.approx(2.0)
    same = _ab_stats.diff_ci(3, 10, 3, 10)
    assert same["diff"] == 0.0
    assert same["low"] < 0 < same["high"]


def test_ab_measures_come_as_table_rows(store: Path) -> None:
    payload = _panel("ab", "t.metrics.q=rate")
    assert [r["measure"] for r in payload["metrics"]] == [
        "redo rate (similar Agent re-dispatched)",
        "follow-up rate (SendMessage after return)",
        "error / aborted rate",
        "user-correction rate (noisy: phrase match)",
    ]
    assert payload["_tables"]["metrics"]["total"] == 8


def test_ab_rows_format_every_measure() -> None:
    arm = {
        "n": 2,
        "usd": {"mean": 1.0, "low": 0.5, "high": 2.0},
        "duration_s": {"mean": 3900.0},
        "redo": {"k": 1, "rate": 0.5, "low": 0.1, "high": 0.9},
        "tags": {"DONE": 2},
    }
    diffs = {"redo": {"diff": -0.05, "low": -0.2, "high": 0.1}}
    rows = {
        r["measure"]: r
        for r in _ab_rows.rows({"arms": {"sonnet": arm}, "diffs": diffs})
    }
    assert rows["n"]["opus"] == "0"
    assert rows["cost per agent (mean, 95% CI)"]["sonnet"] == "$1.00 [$0.50, $2.00]"
    assert rows["cost per agent (mean, 95% CI)"]["opus"] == "—"
    assert rows["duration (mean)"]["sonnet"] == "1h05"
    redo = rows["redo rate (similar Agent re-dispatched)"]
    assert (redo["sonnet"], redo["opus"]) == ("50.0% [10.0%, 90.0%]", "—")
    assert redo["difference"] == "-5.0% [-20.0%, 10.0%]"
    assert rows["error / aborted rate"]["difference"] == "—"
    assert rows["parent session end tag"]["sonnet"] == "DONE 2"
    assert _ab_rows.rows({})[0] == {
        "difference": "",
        "measure": "n",
        "sonnet": "0",
        "opus": "0",
    }
    for seconds, text in ((42.0, "42s"), (420.0, "7m")):
        dur = _ab_rows.rows(
            {"arms": {"opus": {**arm, "duration_s": {"mean": seconds}}}}
        )
        assert dur[2]["opus"] == text
