from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from control_panel.tests import _fixture_prefix as fp
from control_panel.tests import _fixture_tokens as fx
from control_panel.tokens import _api, _db

if TYPE_CHECKING:
    from pathlib import Path

RANGE_CALLS = 4 / 30  # the fixture's four turns, over the default 30 days
TWO_DAYS = (2 * fx.DAY - 1) / fx.DAY  # from=2026-09-28&to=2026-09-29
PRICE = 0.2


@pytest.fixture
def store(sysroot: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(_api, "_now", lambda: fx.T0 + 2 * fx.DAY)
    path = fx.build(sysroot / "home/tester" / _db.STORE)
    files = fp.context_files(path)
    fp.sizes(
        path,
        [
            (files["auto-memory index"], fx.T0 - 2 * fx.DAY, 800, "git"),
            (files["rules"], fx.T0 - 3 * fx.DAY, 400, "git"),
            (files["global CLAUDE.md"], fx.T0 + 600, 2000, "prune 2026-09-28"),
            (files["rules"], fx.T0 + 700, 0, "prune 2026-09-28"),
            (files["repo CLAUDE.md"], fx.T0, 1200, "git"),
            ("/x/topics/a.md", fx.T0, 50, "git"),
        ],
    )
    fp.snapshot(path, "2026-09-29", fx.T0 + fx.DAY, 5000)
    return path


def _prefix(query: str = "") -> dict[str, Any]:
    _, payload = _api.route(["panel", "prefix"], query)
    return payload


def _surfaces(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {r["surface"]: r for r in payload["surfaces"]}


def test_surfaces_start_end_and_cost(store: Path) -> None:
    payload = _prefix("from=2026-09-28&to=2026-09-29")
    rows = _surfaces(payload)
    assert set(rows) == {"global CLAUDE.md", "auto-memory index", "rules"}
    claude = rows["global CLAUDE.md"]
    assert (claude["start_tokens"], claude["tokens"]) == (1000, 500)
    assert claude["delta_tokens"] == -500
    assert claude["files"] == 1
    assert payload["totals"]["calls_per_day"] == pytest.approx(4 / TWO_DAYS)
    assert claude["usd_per_day"] == pytest.approx(500 * 4 / TWO_DAYS * PRICE / 1e6)
    assert rows["rules"]["files"] == 0
    assert payload["surfaces"][0]["surface"] == "global CLAUDE.md"


def test_series_steps_from_the_seed_to_the_range_end(store: Path) -> None:
    payload = _prefix("from=2026-09-28")
    files, audit = payload["series"]
    assert files["label"] == "always-loaded files"
    points = [(p["day"], p["tokens"]) for p in files["points"]]
    assert points == [("2026-09-28", 700), ("2026-09-30", 700)]
    assert [(p["day"], p["tokens"]) for p in audit["points"]] == [("2026-09-29", 5000)]
    quiet = _prefix("from=2026-09-30")
    assert quiet["series"][0]["points"] == [{"day": "2026-09-30", "tokens": 700}]
    assert _surfaces(quiet)["global CLAUDE.md"]["delta_tokens"] == 0
    whole = _prefix()["series"][0]["points"]
    assert [p["day"] for p in whole] == [
        "2026-09-25",
        "2026-09-26",
        "2026-09-27",
        "2026-09-28",
        "2026-09-30",
    ]


def test_totals_price_the_audit_estimate_and_the_files(store: Path) -> None:
    totals = _prefix()["totals"]
    assert totals["audit_tokens"] == 5000
    assert totals["files_tokens"] == 700
    assert totals["calls_per_day"] == pytest.approx(RANGE_CALLS)
    assert totals["audit_usd_per_day"] == pytest.approx(
        5000 * RANGE_CALLS * PRICE / 1e6
    )
    assert totals["files_usd_per_day"] == pytest.approx(700 * RANGE_CALLS * PRICE / 1e6)
    assert totals["pruned_bytes"] == 2400


def test_prune_timeline_has_deltas_vs_the_previous_point(store: Path) -> None:
    rows = _prefix("t.prunes.limit=0")["prunes"]
    first = rows[0]
    assert (first["source"], first["bytes"], first["delta_bytes"]) == (
        "prune 2026-09-28",
        0,
        -400,
    )
    assert first["surface"] == "rules"
    by_path = {r["path"]: r for r in rows}
    assert by_path["/x/topics/a.md"]["surface"] == "not standing"
    assert by_path["/x/topics/a.md"]["delta_bytes"] is None
    assert [r["ts"] for r in rows] == sorted((r["ts"] for r in rows), reverse=True)


@pytest.mark.parametrize(
    ("query", "calls"),
    [
        ("cwd=/home/tester/src", 3),
        ("model=claude-sonnet-5-5", 1),
        ("scope=main", 3),
        ("scope=sub", 1),
        ("from=2026-09-29&to=2026-09-29", 1 * 30 * fx.DAY / (fx.DAY - 1)),
    ],
)
def test_filters_move_calls_per_day_not_the_sizes(
    store: Path, query: str, calls: float
) -> None:
    payload = _prefix(query)
    assert payload["totals"]["calls_per_day"] == pytest.approx(calls / 30)
    assert payload["totals"]["files_tokens"] == 700
    assert "date range" in payload["filtered_by"]


def test_an_empty_range_has_no_rows(store: Path) -> None:
    payload = _prefix("from=2020-01-01&to=2020-01-02")
    assert payload["prunes"] == []
    assert payload["series"][0]["points"] == []
    assert payload["totals"]["audit_tokens"] is None
    assert payload["totals"]["audit_usd_per_day"] is None
    assert payload["surfaces"] == []
