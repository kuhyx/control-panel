from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from control_panel.tests import _fixture_detail as fd
from control_panel.tests import _fixture_subagents as fs
from control_panel.tests import _fixture_tokens as fx
from control_panel.tokens import _anomalies_tokens_rules as rules
from control_panel.tokens import _api, _db

if TYPE_CHECKING:
    from pathlib import Path


def _history() -> list[tuple[object, ...]]:
    """One $1 call a day for the seven days before 2026-09-28."""
    return [
        fs.turn("h", fx.T0 - k * fx.DAY, 1.0, day=f"2026-09-{28 - k:02d}")
        for k in range(1, 8)
    ]


@pytest.fixture
def store(sysroot: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(_api, "_now", lambda: fx.T0 + 2 * fx.DAY)
    path = fx.build(sysroot / "home/tester" / _db.STORE)
    fs.insert(path, turns=[*_history(), fs.turn("s4", fx.T0 + 300, 25.0)])
    fd.insert(
        path,
        calls=[
            fd.call(key="s4", name="Bash", family="sleep", target="sleep 30"),
            fd.call(key="s4", name="Monitor", family="Monitor", target="x"),
            fd.call(key="s4", family="python -m pytest", sig="t1"),
            fd.call(key="s4", family="pnpm lint", sig="t2", carry_usd=0.5),
            fd.call(key="s4", family="ls", sig="l"),
            fd.call(sig="g1"),
            fd.call(key="s1/agent-a", model="claude-sonnet-5-5", sig="g2"),
            fd.call(
                key="s2",
                family="git log",
                ts=fx.T0 + fx.DAY,
                day="2026-09-29",
                cwd="/home/tester",
                sig="g3",
            ),
        ],
    )
    return path


def _anomalies(query: str = "") -> dict[str, Any]:
    _, payload = _api.route(["panel", "anomalies"], query)
    return payload


def test_spikes_are_days_over_twice_the_trailing_median(store: Path) -> None:
    spikes = _anomalies()["spikes"]
    assert [(s["day"], s["usd"]) for s in spikes] == [
        ("2026-09-28", 31.0),
        ("2026-09-29", 4.0),
    ]
    assert spikes[0]["median_usd"] == 1.0
    assert spikes[0]["ratio"] == pytest.approx(31.0)


def test_spikes_use_history_before_the_range(store: Path) -> None:
    spikes = _anomalies("from=2026-09-28&to=2026-09-28")["spikes"]
    assert [s["day"] for s in spikes] == ["2026-09-28"]


def test_expensive_sessions_take_the_over_param(store: Path) -> None:
    payload = _anomalies()
    assert payload["over"] == 20.0
    assert [r["key"] for r in payload["expensive"]] == ["s4"]
    over5 = _anomalies("over=5")["expensive"]
    assert [r["key"] for r in over5] == ["s4", "h", "s1"]
    first = over5[2]
    assert (first["title"], first["cwd"], first["calls"]) == (
        "fix a",
        "/home/tester/src/a",
        3,
    )
    assert _anomalies("over=lots")["over"] == 20.0


def test_categories_classify_polling_lint_test_and_vcs(store: Path) -> None:
    payload = _anomalies()
    rows = {(r["key"], r["category"]): r for r in payload["categories"]}
    assert rows["s4", "polling"]["calls"] == 2
    assert rows["s4", "lint-test"]["cost_usd"] == pytest.approx(0.11 + 0.51)
    assert rows["s1", "vcs"]["calls"] == 2
    assert ("s4", "other") not in rows
    totals = {r["category"]: r["calls"] for r in payload["category_totals"]}
    assert totals == {"polling": 2, "lint-test": 2, "vcs": 3}
    assert payload["categories"][0]["category"] == "lint-test"


def test_loops_use_the_tools_rule(store: Path) -> None:
    assert _anomalies()["loops"] == []


@pytest.mark.parametrize(
    ("query", "spikes", "vcs"),
    [
        ("cwd=/home/tester/src", 1, 2),
        ("model=claude-sonnet-5-5", 0, 1),
        ("scope=main", 2, 2),
        ("scope=sub", 0, 1),
    ],
)
def test_every_filter_applies(store: Path, query: str, spikes: int, vcs: int) -> None:
    payload = _anomalies(query)
    assert len(payload["spikes"]) == spikes
    totals = {r["category"]: r["calls"] for r in payload["category_totals"]}
    assert totals.get("vcs", 0) == vcs


def test_an_empty_range_has_no_rows(store: Path) -> None:
    payload = _anomalies("from=2020-01-01&to=2020-01-02")
    assert payload["spikes"] == []
    assert payload["expensive"] == []
    assert payload["categories"] == []


@pytest.mark.parametrize(
    ("family", "expected"),
    [
        ("", None),
        ("  ", None),
        ("gh run", None),
        ("./poll_ci.sh", "polling"),
        ("until", "polling"),
        ("flutter test", "lint-test"),
        ('python" -m pytest', "lint-test"),
        ("git check-ignore", "vcs"),
    ],
)
def test_category_rule(family: str, expected: str | None) -> None:
    assert rules.category(family) == expected
