from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from control_panel._runner import CommandResult
from control_panel.mutations import _shutdown_hours
from control_panel.tests._fixture_runner import FakeRunner

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def repo(sysroot: Path) -> Path:
    """A screen-locker checkout with the ratchet script present."""
    script = sysroot / "home/tester/screen-locker" / _shutdown_hours.SCRIPT
    script.parent.mkdir(parents=True)
    script.write_text("#!/bin/bash\n")
    return script


def argv_for(script: Path, *hours: int) -> tuple[str, ...]:
    return ("/usr/bin/sudo", str(script), *(str(h) for h in hours))


BODY = {"mon_wed_hour": 21, "thu_sun_hour": 21, "morning_end_hour": 7}


def test_a_stricter_change_is_applied(repo: Path) -> None:
    argv = argv_for(repo, 21, 21, 7)
    runner = FakeRunner(
        {argv: CommandResult(argv=argv, returncode=0, stdout="updated", stderr="")}
    )
    result = _shutdown_hours.apply(runner, BODY)
    assert result.ok
    assert not result.refused
    assert "21:00" in result.summary


def test_the_restore_flag_is_never_passed(repo: Path) -> None:
    # --restore turns the ratchet off. Handing a web UI that flag would defeat
    # the point of having one.
    runner = FakeRunner({})
    _shutdown_hours.apply(runner, BODY)
    assert runner.calls
    assert all("--restore" not in call for call in runner.calls)


def test_a_refusal_relays_the_script_stderr_verbatim(repo: Path) -> None:
    argv = argv_for(repo, 21, 21, 7)
    runner = FakeRunner(
        {
            argv: CommandResult(
                argv=argv,
                returncode=1,
                stdout="",
                stderr="Error: Can only make schedule stricter (a later morning end)",
            )
        }
    )
    result = _shutdown_hours.apply(runner, BODY)
    assert result.refused
    assert not result.ok
    # Relayed, not paraphrased: rewording it would be the dashboard inventing
    # policy it does not own.
    assert "a later morning end" in result.stderr


def test_the_dashboard_never_decides_for_itself(repo: Path) -> None:
    # A loosening the script ACCEPTS is reported as applied. That is the
    # invariant: this module holds no comparator, so it can never be stricter
    # OR looser than the script it delegates to.
    loose = {"mon_wed_hour": 23, "thu_sun_hour": 23, "morning_end_hour": 0}
    argv = argv_for(repo, 23, 23, 0)
    runner = FakeRunner(
        {argv: CommandResult(argv=argv, returncode=0, stdout="", stderr="")}
    )
    assert _shutdown_hours.apply(runner, loose).ok


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"mon_wed_hour": 21},
        {"mon_wed_hour": "x", "thu_sun_hour": 21, "morning_end_hour": 7},
        {"mon_wed_hour": 24, "thu_sun_hour": 21, "morning_end_hour": 7},
        {"mon_wed_hour": -1, "thu_sun_hour": 21, "morning_end_hour": 7},
        "not an object",
        None,
    ],
)
def test_a_malformed_body_is_rejected_before_sudo(repo: Path, body: object) -> None:
    runner = FakeRunner({})
    result = _shutdown_hours.apply(runner, body)
    assert not result.ok
    assert not result.refused
    assert runner.calls == []


def test_a_missing_checkout_is_reported(sysroot: Path) -> None:
    result = _shutdown_hours.apply(FakeRunner({}), BODY)
    assert not result.ok
    assert "screen-locker" in result.summary


def test_a_missing_script_is_reported(sysroot: Path) -> None:
    (sysroot / "home/tester/screen-locker").mkdir(parents=True)
    result = _shutdown_hours.apply(FakeRunner({}), BODY)
    assert "does not exist" in result.summary


def test_a_timeout_is_a_failure_not_a_refusal(repo: Path) -> None:
    argv = argv_for(repo, 21, 21, 7)
    runner = FakeRunner(
        {
            argv: CommandResult(
                argv=argv,
                returncode=None,
                stdout="",
                stderr="",
                timed_out=True,
                error="timed out after 20.0s",
            )
        }
    )
    result = _shutdown_hours.apply(runner, BODY)
    assert not result.ok
    # A refusal means the guard spoke. A timeout means it never did.
    assert not result.refused
    assert "did not run" in result.summary
