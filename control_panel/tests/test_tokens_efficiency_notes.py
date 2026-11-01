"""Efficiency panel: per-note table and weekly USD per note from notes.json."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import pytest

from control_panel.tests import _fixture_tokens as fx
from control_panel.tokens import _api, _db, _efficiency_notes

if TYPE_CHECKING:
    from pathlib import Path

NOTES = "home/tester/.claude/token-report/notes.json"


def _note(note_id: str, status: str, done_at: float | None, usd: float) -> dict:
    return {
        "id": note_id,
        "title": f"note {note_id}",
        "status": status,
        "priority": "high",
        "done_at": done_at,
        "sessions": ["s1", "s2"],
        "usd": usd,
        "tokens": 1000,
    }


@pytest.fixture
def store(sysroot: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(_api, "_now", lambda: fx.T0 + 2 * fx.DAY)
    return fx.build(sysroot / "home/tester" / _db.STORE)


def _write(sysroot: Path, notes: list[Any]) -> None:
    path = sysroot / NOTES
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"generated": fx.T0, "notes": notes}))


def _panel(query: str = "") -> dict[str, Any]:
    _, payload = _api.route(["panel", "efficiency"], query)
    return payload


def test_notes_table_and_weekly_usd_per_note(store: Path, sysroot: Path) -> None:
    _write(
        sysroot,
        [
            _note("a", "done", fx.T0, 12.0),
            _note("b", "abandoned", fx.T0 + 3600, 2.0),
            _note("c", "done", fx.T0 + 7 * fx.DAY, 5.0),
            _note("d", "todo", None, 30.0),
        ],
    )
    payload = _panel("t.notes.sort=-usd")
    assert [r["id"] for r in payload["notes"]] == ["d", "a", "c", "b"]
    assert payload["notes"][0]["sessions"] == 2
    assert payload["notes"][1]["done"] == _db.day_of(fx.T0)
    weeks = {w["week"]: w for w in payload["notes_weekly"]}
    first = weeks[_db.monday(_db.day_of(fx.T0))]
    assert (first["done"], first["abandoned"], first["usd"]) == (1, 1, 14.0)
    assert first["usd_per_note"] == 14.0
    assert "notes" in payload["captions"]


def test_weekly_honours_the_date_range(store: Path, sysroot: Path) -> None:
    _write(sysroot, [_note("a", "done", fx.T0 - 400 * fx.DAY, 1.0)])
    assert _panel()["notes_weekly"] == []
    assert len(_panel()["notes"]) == 1


def test_abandoned_only_week_has_no_ratio(store: Path, sysroot: Path) -> None:
    _write(sysroot, [_note("b", "abandoned", fx.T0, 2.0)])
    assert _panel()["notes_weekly"][0]["usd_per_note"] is None


@pytest.mark.parametrize("text", [None, "not json", '{"notes": 5}', "[]"])
def test_missing_or_bad_file_gives_no_rows(
    store: Path, sysroot: Path, text: str | None
) -> None:
    if text is not None:
        path = sysroot / NOTES
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    payload = _panel()
    assert payload["notes"] == []
    assert payload["notes_weekly"] == []


def test_rows_skip_non_dict_entries(sysroot: Path) -> None:
    _write(sysroot, [5, _note("a", "done", None, 1.0)])
    assert [r["id"] for r in _efficiency_notes.read()] == ["a"]
