from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pytest

from control_panel.sessions import _parse, _scan
from control_panel.tests import _fixture_sessions as fx

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def projects(sysroot: Path) -> Path:
    """The transcripts root under the disposable test tree."""
    return fx.projects_dir(sysroot)


def _one(projects: Path) -> _parse.Session:
    found, scanned = _scan.Scanner().scan(projects)
    assert scanned == 1
    assert list(found) == [fx.SID]
    return found[fx.SID]


@pytest.mark.parametrize(
    ("answer", "status"),
    [
        ("DONE: 3 passed", "done"),
        ("NEEDS ACTION: approve", "needs_action"),
        ("QUESTION: which?", "question"),
        ("RUNNING: CI", "running"),
        ("prose", "untagged"),
        ("DONE: x\nCONTINUING in new session", "continuing"),
        ("DONE: 3 passed\nNOTE: web/ is dirty", "done"),
    ],
)
def test_each_status_class(projects: Path, answer: str, status: str) -> None:
    fx.write(projects, fx.session(answer))
    got = _one(projects)
    assert got.status == status
    assert got.cwd == fx.CWD
    assert got.last_user == "fix the thing"
    assert got.last_assistant.endswith(answer[-20:])
    assert got.last_ts == "2026-10-22T08:00:02.000Z"


def test_a_prompt_after_the_tag_makes_it_untagged(projects: Path) -> None:
    records = fx.session("DONE: shipped")
    records.insert(-2, fx.user("wait, one more thing", "2026-10-22T09:00:00.000Z"))
    fx.write(projects, records)
    got = _one(projects)
    assert got.status == "untagged"
    assert got.last_user == "wait, one more thing"
    assert got.last_ts == "2026-10-22T09:00:00.000Z"


def test_generated_user_records_after_the_tag_do_not_count(projects: Path) -> None:
    records = fx.session("DONE: shipped")
    records.insert(
        -2,
        fx.user("<task-notification>x</task-notification>", "2026-10-22T09:00:00.000Z"),
    )
    records.insert(-2, fx.tool_result("2026-10-22T09:00:01.000Z"))
    fx.write(projects, records)
    assert _one(projects).status == "done"


def test_a_sidechain_assistant_message_is_ignored(projects: Path) -> None:
    records = fx.session("NEEDS ACTION: approve")
    records.insert(
        -2, fx.assistant("DONE: sub", "2026-10-22T08:00:03.000Z", sidechain=True)
    )
    fx.write(projects, records)
    assert _one(projects).status == "needs_action"


def test_a_trailing_tool_only_record_does_not_hide_the_tag(projects: Path) -> None:
    records = fx.session("QUESTION: which?")
    records.insert(-2, fx.assistant(None, "2026-10-22T08:00:03.000Z"))
    fx.write(projects, records)
    assert _one(projects).status == "question"


@pytest.mark.parametrize("entrypoint", ["sdk-cli", "sdk-py"])
def test_sdk_sessions_are_excluded(projects: Path, entrypoint: str) -> None:
    records = fx.session("DONE: x")
    records[1] = fx.user("headless", entrypoint=entrypoint)
    fx.write(projects, records)
    found, scanned = _scan.Scanner().scan(projects)
    assert (found, scanned) == ({}, 1)


def test_sessions_without_a_real_prompt_are_excluded(projects: Path) -> None:
    records = [fx.user("<command-name>/model</command-name>"), *fx.trailer()]
    fx.write(projects, records)
    assert _scan.Scanner().scan(projects)[0] == {}


def test_empty_and_garbage_files_are_skipped(projects: Path) -> None:
    folder = projects / "-x"
    folder.mkdir(parents=True)
    (folder / f"{fx.SID}.jsonl").write_bytes(b"")
    (folder / f"{fx.OTHER_SID}.jsonl").write_bytes(b"{not json\n\n")
    assert _scan.Scanner().scan(projects) == ({}, 2)


def test_subagent_transcripts_in_subdirectories_are_ignored(projects: Path) -> None:
    fx.write(projects, fx.session("DONE: x"))
    nested = projects / "-home-tester-src-demo" / fx.SID / "subagents"
    nested.mkdir(parents=True)
    (nested / f"{fx.OTHER_SID}.jsonl").write_text("{}\n", encoding="utf-8")
    assert list(_scan.Scanner().scan(projects)[0]) == [fx.SID]


def test_the_last_ai_title_wins(projects: Path) -> None:
    records = fx.session("DONE: x")
    records[2:2] = [fx.ai_title("first guess")]
    records[-1:-1] = [fx.ai_title("final title")]
    fx.write(projects, records)
    assert _one(projects).title == "final title"


def test_a_custom_title_beats_the_generated_one(projects: Path) -> None:
    records = [fx.custom_title("my name"), *fx.session("DONE: x"), fx.ai_title("auto")]
    fx.write(projects, records)
    assert _one(projects).title == "my name"


def test_title_falls_back_to_the_first_prompt_line(projects: Path) -> None:
    prompt = "x" * 150 + "\nsecond line"
    records = [
        fx.user("<command-name>/clear</command-name>"),
        *fx.session("DONE: x", prompt),
    ]
    fx.write(projects, records)
    title = _one(projects).title
    assert title.startswith("x" * 99)
    assert len(title) <= 101
    assert "second" not in title


def test_huge_lines_between_the_tag_and_the_end_are_walked(projects: Path) -> None:
    blob = {"type": "api-request-blob", "body": "y" * 300_000}
    records = fx.session("NEEDS ACTION: approve")
    records[-1:-1] = [blob, blob]
    fx.write(projects, records)
    assert _one(projects).status == "needs_action"


def test_a_duplicated_id_keeps_the_newest_transcript(projects: Path) -> None:
    old = fx.write(projects, fx.session("DONE: old"), project_dir="-a")
    fx.write(projects, fx.session("QUESTION: new"), project_dir="-b")
    os.utime(old, ns=(1, 1))
    found, scanned = _scan.Scanner().scan(projects)
    assert scanned == 2
    assert found[fx.SID].status == "question"


def test_an_unchanged_file_is_not_reread(
    projects: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = fx.write(projects, fx.session("DONE: x"))
    reads: list[Path] = []
    real = _parse.read_session

    def counting(path: Path) -> _parse.Session | None:
        reads.append(path)
        return real(path)

    monkeypatch.setattr(_parse, "read_session", counting)
    scanner = _scan.Scanner()
    scanner.scan(projects)
    scanner.scan(projects)
    assert reads == [path]
    # A grown file is a changed key, so it is read again.
    fx.write(projects, [*fx.session("DONE: x"), fx.ai_title("t")])
    assert scanner.scan(projects)[0][fx.SID].title == "t"
    assert len(reads) == 2


def test_a_missing_projects_dir_is_an_empty_scan(projects: Path) -> None:
    assert _scan.Scanner().scan(projects) == ({}, 0)


def test_a_prompt_with_no_reply_is_untagged(projects: Path) -> None:
    records = [fx.assistant(None, "2026-10-22T07:00:00.000Z"), fx.user("hello?")]
    fx.write(projects, records)
    path = projects / "-home-tester-src-demo" / f"{fx.SID}.jsonl"
    with path.open("ab") as handle:
        handle.write(b'{broken "type":"user"\n')
    got = _one(projects)
    assert (got.status, got.last_assistant, got.last_user) == ("untagged", "", "hello?")


def test_malformed_title_records_fall_through_to_an_earlier_one(projects: Path) -> None:
    records = [*fx.session("DONE: x"), fx.ai_title("good"), {"type": "ai-title"}]
    fx.write(projects, records)
    path = projects / "-home-tester-src-demo" / f"{fx.SID}.jsonl"
    with path.open("ab") as handle:
        handle.write(b'{"type":"ai-title","aiTitle":')
    assert _one(projects).title == "good"


def test_unreadable_files_and_dirs_are_skipped(
    projects: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fx.write(projects, fx.session("DONE: x"))
    locked = projects / "-locked"
    locked.mkdir()
    locked.chmod(0)
    try:

        def boom(_path: Path) -> None:
            msg = "gone"
            raise OSError(msg)

        monkeypatch.setattr(_parse, "read_session", boom)
        assert _scan.Scanner().scan(projects) == ({}, 1)
    finally:
        locked.chmod(0o700)


def test_deleted_transcripts_leave_the_cache(projects: Path) -> None:
    path = fx.write(projects, fx.session("DONE: x"))
    scanner = _scan.Scanner()
    assert len(scanner.scan(projects)[0]) == 1
    path.unlink()
    assert scanner.scan(projects) == ({}, 0)
