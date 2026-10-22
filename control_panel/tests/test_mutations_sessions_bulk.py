from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from control_panel.mutations import _session_mark, _session_resume
from control_panel.mutations._session_lookup import known_sessions
from control_panel.sessions import _api
from control_panel.tests import _fixture_sessions as fx
from control_panel.tests._fixture_runner import FakeRunner, ok

if TYPE_CHECKING:
    from pathlib import Path

EPOCH = 1792600000
SIDS = [f"{n}{n}{n}{n}{n}{n}{n}{n}-2222-4333-8444-555555555555" for n in range(1, 7)]


@pytest.fixture(autouse=True)
def marks(sysroot: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Six known sessions, all in the one existing working directory."""
    monkeypatch.setattr(_api, "SCANNER", _api.Scanner())
    monkeypatch.setattr(_session_resume, "now", lambda: EPOCH + 0.7)
    monkeypatch.setattr(_session_mark, "now", lambda: EPOCH + 0.7)
    (sysroot / fx.CWD.lstrip("/")).mkdir(parents=True)
    for sid in SIDS:
        fx.write(fx.projects_dir(sysroot), fx.session("DONE: ok"), sid=sid)
    return sysroot / "home/tester/.claude/session-status.json"


def _argv(sid: str) -> tuple[str, ...]:
    return _session_resume.build_argv(
        sid, fx.CWD, ":0", "/home/tester/.Xauthority", EPOCH
    )


@pytest.mark.parametrize(
    "body",
    [
        {"ids": []},
        {"ids": "not-a-list"},
        {"ids": [SIDS[0]], "id": SIDS[1]},
    ],
)
def test_lookup_rejects_a_malformed_ids_field(body: object) -> None:
    result = known_sessions(body)
    assert not isinstance(result, list)
    assert not result.ok


def test_lookup_dedupes_and_keeps_order() -> None:
    found = known_sessions({"ids": [SIDS[2], SIDS[0], SIDS[2]]})
    assert isinstance(found, list)
    assert [s.id for s in found] == [SIDS[2], SIDS[0]]


def test_lookup_names_every_bad_id() -> None:
    result = known_sessions({"ids": [SIDS[0], "nope", fx.OTHER_SID, 7]})
    assert not isinstance(result, list)
    assert result.refused
    for bad in ("'nope'", fx.OTHER_SID, "7"):
        assert bad in result.summary
        assert bad in result.stderr
    assert SIDS[0] not in result.summary


def test_lookup_summary_truncates_a_long_bad_list() -> None:
    bad = [f"bad-{n}" for n in range(9)]
    result = known_sessions({"ids": bad})
    assert not isinstance(result, list)
    assert "+4 more" in result.summary
    assert "bad-8" in result.stderr


def test_bulk_mark_done_then_clear(marks: Path) -> None:
    result = _session_mark.apply(FakeRunner({}), {"ids": SIDS[:4], "mark": "done"})
    assert result.ok, result
    assert result.summary == "Marked 4 sessions done."
    stored = json.loads(marks.read_text())
    assert stored == {sid: {"mark": "done", "at": EPOCH} for sid in SIDS[:4]}
    result = _session_mark.apply(FakeRunner({}), {"ids": SIDS[:1], "mark": None})
    assert result.summary == "Unmarked 1 session."
    assert set(json.loads(marks.read_text())) == set(SIDS[1:4])


def test_bulk_mark_with_one_bad_id_writes_nothing(marks: Path) -> None:
    body = {"ids": [SIDS[0], fx.OTHER_SID, SIDS[1]], "mark": "done"}
    result = _session_mark.apply(FakeRunner({}), body)
    assert result.refused
    assert fx.OTHER_SID in result.summary
    assert not marks.exists()


def test_bulk_resume_launches_one_terminal_per_id() -> None:
    argvs = [_argv(sid) for sid in SIDS[:5]]
    runner = FakeRunner({argv: ok(argv, f"unit {n}") for n, argv in enumerate(argvs)})
    result = _session_resume.apply(runner, {"ids": SIDS[:5]})
    assert result.ok, result
    assert result.summary == "Resuming 5 sessions in new terminals."
    assert runner.calls[1:] == argvs
    assert "unit 4" in result.stdout


def test_bulk_resume_over_the_cap_launches_nothing() -> None:
    runner = FakeRunner({})
    result = _session_resume.apply(runner, {"ids": SIDS})
    assert result.refused
    assert "5" in result.summary
    assert runner.calls == []


def test_bulk_resume_with_one_bad_id_launches_nothing() -> None:
    runner = FakeRunner({})
    result = _session_resume.apply(runner, {"ids": [SIDS[0], "x"]})
    assert result.refused
    assert runner.calls == []


def test_bulk_resume_with_a_vanished_directory_launches_nothing(
    sysroot: Path,
) -> None:
    other = "/home/tester/src/gone"
    records = [fx.user("hi", cwd=other), fx.assistant("DONE: ok", cwd=other)]
    fx.write(fx.projects_dir(sysroot), records, sid=fx.OTHER_SID, project_dir="-g")
    runner = FakeRunner({})
    result = _session_resume.apply(runner, {"ids": [SIDS[0], fx.OTHER_SID]})
    assert not result.ok
    assert other in result.summary
    assert runner.calls == []


def test_bulk_resume_stops_at_the_first_failed_launch() -> None:
    first = _argv(SIDS[0])
    runner = FakeRunner({first: ok(first, "")})
    result = _session_resume.apply(runner, {"ids": SIDS[:3]})
    assert not result.ok
    assert "1 of 3" in result.summary
    assert runner.calls[1:] == [first, _argv(SIDS[1])]
