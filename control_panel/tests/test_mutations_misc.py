from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from control_panel._runner import CommandResult
from control_panel.mutations import _repos, _steam_view, _types
from control_panel.tests._fixture_runner import FakeRunner

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

CONFIG = "home/tester/.config/steam_backlog_enforcer"


def test_steam_view_is_read_only_and_says_why(sysroot: Path) -> None:
    view = _steam_view.view()
    assert view["read_only"] is True
    # Offering a control that silently does nothing is worse than offering none.
    assert "chattr +i" in view["why_read_only"]


def test_steam_view_reads_approved_exceptions_and_audit(sysroot: Path) -> None:
    base = sysroot / CONFIG
    base.mkdir(parents=True)
    (base / _steam_view.APPROVED).write_text(
        json.dumps([{"app_id": 880940, "reason": "party game"}])
    )
    (base / _steam_view.AUDIT).write_text(
        "2026-05-31T19:52:51Z | APPROVED | app_id=880940 | reason='party game'\n"
    )
    view = _steam_view.view()
    assert view["approved"][0]["app_id"] == 880940
    assert "party game" in view["audit"][0]
    assert view["unreadable"] is None


def test_no_approvals_yet_is_not_an_error(sysroot: Path) -> None:
    view = _steam_view.view()
    assert view["approved"] == []
    assert "ever been approved" in view["unreadable"]


def test_an_unreadable_approvals_file_is_reported_not_escalated(
    sysroot: Path,
) -> None:
    # Several of this daemon's files are root-owned 0600. kuhy has NOPASSWD,
    # so sudo would work -- and not doing it is what keeps this an observer.
    base = sysroot / CONFIG
    base.mkdir(parents=True)
    (base / _steam_view.APPROVED).write_text("{{{ not json")
    view = _steam_view.view()
    assert view["approved"] == []
    assert "could not be read" in view["unreadable"]


def test_a_non_list_approvals_file_is_reported(sysroot: Path) -> None:
    base = sysroot / CONFIG
    base.mkdir(parents=True)
    (base / _steam_view.APPROVED).write_text('{"app_id": 1}')
    assert "not a list" in _steam_view.view()["unreadable"]


def test_non_object_entries_are_dropped(sysroot: Path) -> None:
    base = sysroot / CONFIG
    base.mkdir(parents=True)
    (base / _steam_view.APPROVED).write_text(json.dumps([{"app_id": 1}, "junk", 3]))
    assert _steam_view.view()["approved"] == [{"app_id": 1}]


def test_repo_resolution_prefers_the_shared_resolver(sysroot: Path) -> None:
    script = sysroot / "home/tester/src/testsAndMisc/linux_configuration/lib"
    script.mkdir(parents=True)
    (script / "extracted_repos.sh").write_text("#!/bin/bash\n")
    target = sysroot / "home/tester/elsewhere/screen-locker"
    target.mkdir(parents=True)
    argv = (
        "bash",
        "-c",
        f'source "{script / "extracted_repos.sh"}"; extracted_repo_dir "screen-locker"',
    )
    runner = FakeRunner(
        {
            argv: CommandResult(
                argv=argv,
                returncode=0,
                stdout="/home/tester/elsewhere/screen-locker\n",
                stderr="",
            )
        }
    )
    found = _repos.locate(runner, "screen-locker")
    assert found.path == target


def test_a_resolver_pointing_at_nothing_is_reported(sysroot: Path) -> None:
    script = sysroot / "home/tester/src/testsAndMisc/linux_configuration/lib"
    script.mkdir(parents=True)
    (script / "extracted_repos.sh").write_text("#!/bin/bash\n")
    argv = (
        "bash",
        "-c",
        f'source "{script / "extracted_repos.sh"}"; extracted_repo_dir "ghost"',
    )
    runner = FakeRunner(
        {argv: CommandResult(argv=argv, returncode=0, stdout="/nope\n", stderr="")}
    )
    found = _repos.locate(runner, "ghost")
    assert found.path is None
    assert "does not exist" in found.detail


def test_the_conventional_location_is_the_fallback(sysroot: Path) -> None:
    # No resolver on disk: the convention it encodes is still the right answer.
    (sysroot / "home/tester/hosts-blocker").mkdir(parents=True)
    assert _repos.locate(FakeRunner({}), "hosts-blocker").path is not None


def test_a_missing_repo_reports_where_it_looked(sysroot: Path) -> None:
    found = _repos.locate(FakeRunner({}), "nowhere")
    assert found.path is None
    assert "nowhere" in found.detail


def test_a_failing_resolver_falls_back(sysroot: Path) -> None:
    script = sysroot / "home/tester/src/testsAndMisc/linux_configuration/lib"
    script.mkdir(parents=True)
    (script / "extracted_repos.sh").write_text("#!/bin/bash\n")
    (sysroot / "home/tester/diet-guard").mkdir(parents=True)
    assert _repos.locate(FakeRunner({}), "diet-guard").path is not None


@pytest.mark.parametrize(
    ("factory", "expect"),
    [
        (lambda: _types.MutationResult.success("done"), (True, False)),
        (lambda: _types.MutationResult.refusal("no", "stderr"), (False, True)),
        (lambda: _types.MutationResult.failure("broken"), (False, False)),
    ],
)
def test_result_constructors_distinguish_refusal_from_failure(
    factory: Callable[[], _types.MutationResult], expect: tuple[bool, bool]
) -> None:
    # A refusal is the ratchet working; a failure is the machinery broken. The
    # UI colours them differently, so they must not collapse.
    result = factory()
    assert (result.ok, result.refused) == expect
    assert json.dumps(_types.to_payload(result))
