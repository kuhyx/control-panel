from __future__ import annotations

from http import HTTPStatus
import json
from typing import TYPE_CHECKING

import pytest

from control_panel import _routes
from control_panel.sessions import _api
from control_panel.tests import _fixture_sessions as fx

if TYPE_CHECKING:
    from pathlib import Path

KEYS = {
    "id",
    "cwd",
    "project",
    "title",
    "status",
    "done",
    "manual_mark",
    "last_ts",
    "last_user",
    "last_assistant",
    "resume_command",
}


@pytest.fixture(autouse=True)
def fresh_scanner(monkeypatch: pytest.MonkeyPatch) -> None:
    """A per-test cache, so one test's transcripts never leak into the next."""
    monkeypatch.setattr(_api, "SCANNER", _api.Scanner())


def _sid(n: int) -> str:
    return f"{n:08d}-0000-4000-8000-000000000000"


def _get(path: str = "/api/sessions") -> tuple[HTTPStatus, dict]:
    resolved = _routes.Router(object(), 8770).resolve(path)
    assert resolved is not None
    return resolved


def test_route_serves_the_contract_shape(sysroot: Path) -> None:
    fx.write(fx.projects_dir(sysroot), fx.session("NEEDS ACTION: approve"))
    status, payload = _get()
    assert status is HTTPStatus.OK
    assert set(payload) == {"sessions", "scanned", "scan_ms"}
    assert payload["scanned"] == 1
    assert isinstance(payload["scan_ms"], float)
    (row,) = payload["sessions"]
    assert set(row) == KEYS
    assert row["id"] == fx.SID
    assert row["project"] == "demo"
    assert row["status"] == "needs_action"
    assert row["done"] is False
    assert row["manual_mark"] is None
    assert row["resume_command"] == f"cd '{fx.CWD}' && claude --resume {fx.SID}"
    json.dumps(payload)


def test_unknown_subpath_is_404() -> None:
    assert _get("/api/sessions/nope")[0] is HTTPStatus.NOT_FOUND


def test_text_fields_are_bounded(sysroot: Path) -> None:
    answer = "z" * 2000 + "\nDONE: tail visible"
    fx.write(fx.projects_dir(sysroot), fx.session(answer, "p" * 2000))
    (row,) = _get()[1]["sessions"]
    assert len(row["last_user"]) <= 400
    assert len(row["last_assistant"]) <= 600
    assert row["last_assistant"].endswith("DONE: tail visible")


def test_home_cwd_is_shown_as_tilde_and_quotes_are_escaped(sysroot: Path) -> None:
    projects = fx.projects_dir(sysroot)
    records = fx.session("DONE: x")
    records[1] = fx.user("hi", cwd=fx.HOME)
    fx.write(projects, records, sid=_sid(1))
    records[1] = fx.user("hi", cwd="/srv/it's")
    fx.write(projects, records, sid=_sid(2), project_dir="-srv")
    rows = {r["id"]: r for r in _get()[1]["sessions"]}
    assert rows[_sid(1)]["project"] == "~"
    assert rows[_sid(2)]["resume_command"].startswith("cd '/srv/it'\\''s' && ")


def test_sorted_by_group_then_newest_first(sysroot: Path) -> None:
    projects = fx.projects_dir(sysroot)
    plan = [
        (1, "DONE: a", "08"),
        (2, "RUNNING: b", "09"),
        (3, "prose", "10"),
        (4, "QUESTION: c", "11"),
        (5, "NEEDS ACTION: d", "07"),
        (6, "NEEDS ACTION: e", "12"),
        (7, "DONE: f\nCONTINUING in new session", "13"),
        (8, "QUESTION: marked done by hand", "14"),
    ]
    for n, answer, hour in plan:
        records = fx.session(answer)
        records[4] = fx.assistant(answer, f"2026-10-22T{hour}:00:00.000Z")
        fx.write(projects, records, sid=_sid(n))
    marks = sysroot / "home/tester/.claude/session-status.json"
    marks.write_text(json.dumps({_sid(8): {"mark": "done", "at": 1}}), "utf-8")
    rows = _get()[1]["sessions"]
    assert [r["id"] for r in rows] == [_sid(n) for n in (6, 5, 4, 3, 2, 8, 7, 1)]
    marked = rows[5]
    assert (marked["status"], marked["done"], marked["manual_mark"]) == (
        "question",
        True,
        "done",
    )


def test_unreadable_marks_file_is_no_marks(sysroot: Path) -> None:
    fx.write(fx.projects_dir(sysroot), fx.session("QUESTION: x"))
    marks = sysroot / "home/tester/.claude/session-status.json"
    marks.write_text("{oops", "utf-8")
    (row,) = _get()[1]["sessions"]
    assert row["manual_mark"] is None


def test_a_marks_file_that_is_not_an_object_is_no_marks(sysroot: Path) -> None:
    fx.write(fx.projects_dir(sysroot), fx.session("QUESTION: x"))
    marks = sysroot / "home/tester/.claude/session-status.json"
    marks.write_text(json.dumps([fx.SID]), "utf-8")
    (row,) = _get()[1]["sessions"]
    assert row["done"] is False
