from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from control_panel.tests import _fixture_subagents as fs
from control_panel.tests import _fixture_tokens as fx
from control_panel.tokens import _api, _db

if TYPE_CHECKING:
    from pathlib import Path

HERE = "HERE: " + "x" * 114


@pytest.fixture
def store(sysroot: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(_api, "_now", lambda: fx.T0 + 2 * fx.DAY)
    path = fx.build(sysroot / "home/tester" / _db.STORE)
    fs.insert(
        path,
        turns=[fs.turn("s3", fx.T0 + 300, 0.5, cwd="/home/tester/src/b")],
        prompts=[
            ("s1", 0, fx.T0, "p0", "LONG: fix a thing"),
            ("s1", 1, fx.T0 + 3600, "p1", "override"),
            ("s2", 0, fx.T0 + fx.DAY, "p2", HERE),
            ("s3", 0, fx.T0 + 299, "p5", "/clear"),
            ("s3", 1, fx.T0 + 300, "p3", "SOLVE: two sum"),
            ("s3", 2, fx.T0 + 301, "p6", "and why"),
            ("s3", 3, fx.T0 - 60 * fx.DAY, "p7", "OPUS: before the range"),
            ("old", 0, fx.T0 - 90 * fx.DAY, "p4", "LONG: old"),
        ],
    )
    return path


def _habits(query: str = "") -> dict[str, Any]:
    _, payload = _api.route(["panel", "prompt_habits"], query)
    return payload


def test_opening_prompt_length_vs_session_cost(store: Path) -> None:
    payload = _habits()
    sessions = {r["key"]: r for r in payload["sessions"]}
    assert (sessions["s1"]["length"], sessions["s1"]["usd"]) == (17, 6.0)
    assert sessions["s2"]["length"] == 120
    assert payload["sessions"][0]["key"] == "s1"
    buckets = {r["bucket"]: r for r in payload["length_buckets"] if r["sessions"]}
    assert buckets["1-20"]["sessions"] == 2
    assert buckets["1-20"]["mean_usd"] == pytest.approx(3.25)
    assert buckets["120 (truncated)"]["total_usd"] == 4.0
    assert "120" in payload["caption"]


def test_prefix_counts(store: Path) -> None:
    rows = {r["prefix"]: r for r in _habits()["prefixes"]}
    assert (rows["LONG:"]["prompts"], rows["LONG:"]["session_usd"]) == (1, 6.0)
    assert rows["override"]["sessions"] == 1
    assert rows["HERE:"]["session_usd"] == 4.0
    assert rows["SOLVE:"]["prompts"] == 1
    assert rows["OPUS:"]["prompts"] == 0


def test_sessions_started_from_home(store: Path) -> None:
    home = _habits()["home"]
    assert (home["sessions"], home["usd"]) == (1, 4.0)
    assert home["usd_share"] == pytest.approx(4.0 / 10.5)
    assert home["session_share"] == pytest.approx(1 / 3)


@pytest.mark.parametrize(
    ("query", "sessions", "home"),
    [
        ("cwd=/home/tester/src", 2, 0),
        ("model=claude-sonnet-5-5", 1, 0),
        ("scope=main", 3, 1),
        ("scope=sub", 1, 0),
        ("from=2026-09-29&to=2026-09-29", 1, 1),
    ],
)
def test_every_filter_applies(
    store: Path, query: str, sessions: int, home: int
) -> None:
    payload = _habits(query)
    assert len(payload["sessions"]) == sessions
    assert payload["home"]["sessions"] == home


def test_an_empty_range_has_no_rows(store: Path) -> None:
    payload = _habits("from=2020-01-01&to=2020-01-02")
    assert payload["sessions"] == []
    assert payload["home"]["usd_share"] is None
    assert all(r["prompts"] == 0 for r in payload["prefixes"])
