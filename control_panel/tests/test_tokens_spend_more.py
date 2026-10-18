from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

import pytest

from control_panel.tests import _fixture_detail as fd
from control_panel.tests import _fixture_subagents as fs
from control_panel.tests import _fixture_tokens as fx
from control_panel.tokens import _api, _db

if TYPE_CHECKING:
    from pathlib import Path

RANGE = "from=2026-08-01&to=2026-09-30"
HOUR = 3600


@pytest.fixture
def store(sysroot: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(_api, "_now", lambda: fx.T0 + 2 * fx.DAY)
    path = fx.build(sysroot / "home/tester" / _db.STORE)
    fs.insert(
        path,
        turns=[
            fs.turn("s5", fx.T0 - 40 * fx.DAY, 5.0, day="2026-08-19"),
            fs.turn("s3", fx.T0 + 5 * HOUR + 10, 0.5),
            fs.turn("s6", fx.T0 - 75 * fx.DAY, 1.0, day="2026-07-15"),
            fs.turn("s7", fx.T0 - 105 * fx.DAY, 1.0, day="2026-06-15"),
        ],
    )
    fd.insert(
        path,
        marks=[
            fd.mark(kind="api_error", name="rate_limit", detail="429", count=3),
            fd.mark(kind="api_error", name="model_not_found", detail="", count=1),
        ],
    )
    return path


def _spend(query: str = "") -> dict[str, Any]:
    _, payload = _api.route(["panel", "spend_more"], query)
    return payload


def test_months_and_cumulative_in_month(store: Path) -> None:
    payload = _spend(RANGE)
    assert [(m["month"], m["usd"]) for m in payload["months"]] == [
        ("2026-09", 10.5),
        ("2026-08", 5.0),
    ]
    cumulative = [(r["month"], r["dom"], r["cum_usd"]) for r in payload["cumulative"]]
    assert cumulative == [
        ("2026-08", 19, 5.0),
        ("2026-09", 28, 6.5),
        ("2026-09", 29, 10.5),
    ]


def test_cumulative_keeps_the_last_three_months(store: Path) -> None:
    rows = _spend("from=2026-06-01&to=2026-09-30")["cumulative"]
    assert sorted({r["month"] for r in rows}) == ["2026-07", "2026-08", "2026-09"]


def test_spend_by_model_and_by_cwd(store: Path) -> None:
    payload = _spend()
    models = [(r["model"], r["usd"]) for r in payload["by_model"]]
    assert models == [("claude-opus-5-5", 7.5), ("claude-sonnet-5-5", 3.0)]
    assert payload["by_model"][0]["share"] == pytest.approx(7.5 / 10.5)
    cwds = [(r["cwd"], r["usd"]) for r in payload["by_cwd"]]
    assert cwds == [("/home/tester/src/a", 6.5), ("/home/tester", 4.0)]


def test_heatmap_by_local_weekday_and_hour(store: Path) -> None:
    local = datetime.fromtimestamp(fx.T0).astimezone()
    cells = {(c["weekday"], c["hour"]): c for c in _spend()["heatmap"]}
    cell = cells[local.weekday(), local.hour]
    assert cell["usd"] == pytest.approx(5.0)
    assert cell["calls"] == 2
    assert _spend()["heatmap"][0]["usd"] == pytest.approx(5.0)


def test_five_hour_blocks(store: Path) -> None:
    payload = _spend()
    blocks = payload["blocks"]
    assert [(b["usd"], b["calls"]) for b in blocks] == [(6.0, 3), (4.0, 1), (0.5, 1)]
    first = blocks[0]
    assert (first["start"], first["end"]) == (fx.T0, fx.T0 + 5 * HOUR)
    assert first["usd_per_hour"] == pytest.approx(6.0)
    assert blocks[1]["usd_per_hour"] is None
    assert blocks[2]["start"] == fx.T0 + 5 * HOUR
    daily = [
        (d["day"], d["blocks"], d["max_block_usd"]) for d in payload["block_daily"]
    ]
    assert daily == [("2026-09-28", 2, 6.0), ("2026-09-29", 1, 4.0)]
    assert "5-hour" in payload["caption"]


def test_rate_limit_errors_per_day(store: Path) -> None:
    assert _spend()["rate_limits"] == [{"day": "2026-09-28", "errors": 3}]


@pytest.mark.parametrize(
    ("query", "usd", "errors"),
    [
        ("cwd=/home/tester/src", 6.5, 3),
        ("model=claude-sonnet-5-5", 3.0, 0),
        ("scope=main", 7.5, 3),
        ("scope=sub", 3.0, 0),
        ("from=2026-09-29&to=2026-09-29", 4.0, 0),
    ],
)
def test_every_filter_applies(store: Path, query: str, usd: float, errors: int) -> None:
    payload = _spend(query)
    assert sum(r["usd"] for r in payload["by_model"]) == pytest.approx(usd)
    assert sum(b["usd"] for b in payload["blocks"]) == pytest.approx(usd)
    assert sum(r["errors"] for r in payload["rate_limits"]) == errors


def test_an_empty_range_has_no_rows(store: Path) -> None:
    payload = _spend("from=2020-01-01&to=2020-01-02")
    assert payload["months"] == []
    assert payload["blocks"] == []
    assert payload["heatmap"] == []
    assert payload["totals"]["usd"] == 0
