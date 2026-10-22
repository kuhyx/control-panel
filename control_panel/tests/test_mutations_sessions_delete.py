from __future__ import annotations

from http import HTTPStatus
import json
import os
import pathlib
import time
from typing import TYPE_CHECKING

import pytest

from control_panel import _routes
from control_panel.mutations import _session_delete
from control_panel.sessions import _api
from control_panel.tests import _fixture_sessions as fx
from control_panel.tests._fixture_runner import FakeRunner

if TYPE_CHECKING:
    from pathlib import Path

    from control_panel.mutations._types import MutationResult

EPOCH = 1792600000
OLD = EPOCH - 3600
DAY = time.strftime("%Y-%m-%d", time.localtime(EPOCH))
PROJECT = "-home-tester-src-demo"
SIDS = [fx.SID, fx.OTHER_SID]


def _write(projects: Path, sid: str, project_dir: str = PROJECT) -> Path:
    path = fx.write(projects, fx.session("DONE: ok"), sid=sid, project_dir=project_dir)
    os.utime(path, (OLD, OLD))
    return path


@pytest.fixture
def projects(sysroot: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Two known, hour-old sessions; the first has a subagent directory."""
    monkeypatch.setattr(_api, "SCANNER", _api.Scanner())
    monkeypatch.setattr(_session_delete, "now", lambda: EPOCH + 0.7)
    root = fx.projects_dir(sysroot)
    for sid in SIDS:
        _write(root, sid)
    sub = root / PROJECT / fx.SID / "subagents"
    sub.mkdir(parents=True)
    (sub / "agent-a.jsonl").write_text("{}\n")
    marks = sysroot / "home/tester/.claude/session-status.json"
    marks.write_text(json.dumps({sid: {"mark": "done", "at": 1} for sid in SIDS}))
    _api.route([], "")
    return root


def _trash(sysroot: Path) -> Path:
    return sysroot / "home/tester/.claude/projects-trash" / DAY / PROJECT


def _marks(sysroot: Path) -> dict[str, object]:
    raw = (sysroot / "home/tester/.claude/session-status.json").read_text()
    return json.loads(raw)


def _delete(body: object) -> MutationResult:
    return _session_delete.apply(FakeRunner({}), body)


def _cached_ids() -> set[str]:
    return {p.rsplit("/", 1)[-1].removesuffix(".jsonl") for p in _api.SCANNER.cached()}


def test_delete_one_moves_transcript_and_subagents(
    projects: Path, sysroot: Path
) -> None:
    result = _delete({"id": fx.SID})
    assert result.ok, result
    assert result.summary == (
        f"Moved 1 session to ~/.claude/projects-trash/{DAY} "
        "(restore by moving them back)."
    )
    trash = _trash(sysroot)
    assert (trash / f"{fx.SID}.jsonl").is_file()
    assert (trash / fx.SID / "subagents/agent-a.jsonl").is_file()
    assert not (projects / PROJECT / f"{fx.SID}.jsonl").exists()
    assert not (projects / PROJECT / fx.SID).exists()
    assert set(_marks(sysroot)) == {fx.OTHER_SID}
    # Forgotten at once, not only on the next scan.
    assert fx.SID not in _cached_ids()
    assert fx.OTHER_SID in _cached_ids()
    rows = _api.route([], "")[1]["sessions"]
    assert [r["id"] for r in rows] == [fx.OTHER_SID]


def test_delete_bulk_moves_every_copy(projects: Path, sysroot: Path) -> None:
    # A moved repo: the same id in a second project dir must go too.
    _write(projects, fx.OTHER_SID, "-old-demo")
    result = _delete({"ids": SIDS})
    assert result.ok, result
    assert result.summary.startswith("Moved 2 sessions to ")
    assert (_trash(sysroot) / f"{fx.OTHER_SID}.jsonl").is_file()
    old = sysroot / "home/tester/.claude/projects-trash" / DAY / "-old-demo"
    assert (old / f"{fx.OTHER_SID}.jsonl").is_file()
    assert _marks(sysroot) == {}
    assert _api.route([], "")[1]["sessions"] == []


def test_delete_skips_the_marks_write_when_unmarked(
    projects: Path, sysroot: Path
) -> None:
    marks = sysroot / "home/tester/.claude/session-status.json"
    marks.unlink()
    assert _delete({"id": fx.SID}).ok
    assert not marks.exists()
    assert projects.is_dir()


@pytest.mark.usefixtures("projects")
@pytest.mark.parametrize("age", [0, 599, -60])
def test_delete_refuses_a_recently_written_transcript(age: int, sysroot: Path) -> None:
    fresh = fx.projects_dir(sysroot) / PROJECT / f"{fx.OTHER_SID}.jsonl"
    os.utime(fresh, (EPOCH - age, EPOCH - age))
    result = _delete({"ids": SIDS})
    assert result.refused
    assert fx.OTHER_SID in result.summary
    assert fx.SID not in result.summary
    assert not (sysroot / "home/tester/.claude/projects-trash").exists()


@pytest.mark.usefixtures("projects")
@pytest.mark.parametrize(
    "body", [None, [], "x", {"id": "not-a-uuid"}, {"ids": [fx.SID, "nope"]}]
)
def test_delete_refuses_bad_bodies_and_moves_nothing(
    body: object, sysroot: Path
) -> None:
    assert not _delete(body).ok
    assert not (sysroot / "home/tester/.claude/projects-trash").exists()
    assert len(_marks(sysroot)) == len(SIDS)


@pytest.mark.usefixtures("projects")
def test_delete_refuses_an_unknown_id(sysroot: Path) -> None:
    result = _delete({"ids": [fx.SID, "aaaaaaaa-2222-4333-8444-555555555555"]})
    assert result.refused
    assert "aaaaaaaa" in result.summary
    assert not (sysroot / "home/tester/.claude/projects-trash").exists()


def test_delete_refuses_a_symlinked_transcript(projects: Path, sysroot: Path) -> None:
    outside = sysroot / "elsewhere.jsonl"
    path = projects / PROJECT / f"{fx.OTHER_SID}.jsonl"
    path.rename(outside)
    path.symlink_to(outside)
    os.utime(outside, (OLD, OLD))
    result = _delete({"ids": SIDS})
    assert result.refused
    assert fx.OTHER_SID in result.summary
    assert outside.is_file()
    assert not (sysroot / "home/tester/.claude/projects-trash").exists()


def test_delete_refuses_a_symlinked_subagent_dir(projects: Path, sysroot: Path) -> None:
    outside = sysroot / "elsewhere"
    outside.mkdir()
    (projects / PROJECT / fx.OTHER_SID).symlink_to(outside)
    result = _delete({"id": fx.OTHER_SID})
    assert result.refused
    assert fx.OTHER_SID in result.summary
    assert (projects / PROJECT / f"{fx.OTHER_SID}.jsonl").is_file()


def test_delete_refuses_to_overwrite_the_trash(projects: Path, sysroot: Path) -> None:
    trash = _trash(sysroot)
    trash.mkdir(parents=True)
    (trash / f"{fx.SID}.jsonl").write_text("earlier copy\n")
    result = _delete({"id": fx.SID})
    assert result.refused
    assert (trash / f"{fx.SID}.jsonl").read_text() == "earlier copy\n"
    assert (projects / PROJECT / f"{fx.SID}.jsonl").is_file()


def test_delete_reports_a_failed_move(
    projects: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def refuse(_src: object, _dst: object) -> None:
        msg = "read-only file system"
        raise OSError(msg)

    monkeypatch.setattr(pathlib.Path, "rename", refuse)
    result = _delete({"ids": SIDS})
    assert not result.ok
    assert not result.refused
    assert "read-only" in result.stderr
    assert (projects / PROJECT / f"{fx.SID}.jsonl").is_file()


@pytest.mark.usefixtures("projects")
def test_delete_reports_a_failed_marks_write(
    sysroot: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def refuse(_src: object, _dst: object) -> None:
        msg = "disk full"
        raise OSError(msg)

    monkeypatch.setattr(pathlib.Path, "replace", refuse)
    result = _delete({"id": fx.SID})
    assert not result.ok
    assert "disk full" in result.stderr
    assert (_trash(sysroot) / f"{fx.SID}.jsonl").is_file()


@pytest.mark.usefixtures("projects")
def test_router_dispatches_session_delete() -> None:
    status, payload = _routes.Router(FakeRunner({}), 8770).mutate(
        "session-delete", {"id": "x"}
    )
    assert status is HTTPStatus.OK
    assert payload["ok"] is False
