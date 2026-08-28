from __future__ import annotations

import os
from pathlib import Path
import signal

import pytest

from control_panel import _port_guard
from control_panel.tests._fixture_runner import FakeRunner, ok

SS = ("ss", "-tlnp")
LINE = 'LISTEN 0 5 127.0.0.1:8770 0.0.0.0:* users:(("python3",pid=2359343,fd=3))'


@pytest.fixture(autouse=True)
def _no_signals(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail loudly if anything in this module ever signals a process.

    The whole design decision here is that a read-only dashboard refuses the
    port rather than reaping its owner, so that is asserted, not commented.
    """

    def forbidden(*_args: object, **_kwargs: object) -> None:
        msg = "control-panel must never signal another process"
        raise AssertionError(msg)

    monkeypatch.setattr(os, "kill", forbidden)
    monkeypatch.setattr(signal, "raise_signal", forbidden)


def test_identifies_the_owner_by_pid() -> None:
    runner = FakeRunner({SS: ok(SS, LINE)})
    owner = _port_guard.identify_owner(runner, 8770)
    assert owner.pid == 2359343


def test_unknown_owner_when_ss_fails() -> None:
    owner = _port_guard.identify_owner(FakeRunner({}), 8770)
    assert owner.pid is None
    assert "unidentified" in owner.describe()


def test_unknown_owner_when_no_line_matches() -> None:
    runner = FakeRunner({SS: ok(SS, "LISTEN 0 5 127.0.0.1:22 0.0.0.0:*")})
    assert _port_guard.identify_owner(runner, 8770).pid is None


def test_short_lines_are_skipped() -> None:
    runner = FakeRunner({SS: ok(SS, "garbage\n")})
    assert _port_guard.identify_owner(runner, 8770).pid is None


def test_line_without_a_pid_is_skipped() -> None:
    runner = FakeRunner({SS: ok(SS, "LISTEN 0 5 127.0.0.1:8770 0.0.0.0:*")})
    assert _port_guard.identify_owner(runner, 8770).pid is None


def test_describes_a_fully_identified_owner() -> None:
    owner = _port_guard.PortOwner(pid=7, exe="/usr/bin/python3", cmdline="-m x")
    described = owner.describe()
    assert "pid 7" in described
    assert "/usr/bin/python3" in described
    assert "(-m x)" in described


def test_describes_a_partially_identified_owner() -> None:
    assert _port_guard.PortOwner(pid=7, exe=None, cmdline=None).describe() == "pid 7"


def test_refusal_names_the_owner_and_refuses() -> None:
    runner = FakeRunner({SS: ok(SS, LINE)})
    message = _port_guard.refusal_message(runner, 8770)
    assert "2359343" in message
    assert "will not stop it" in message


def test_reads_the_running_process_own_proc_entries() -> None:
    owner = _port_guard.PortOwner(
        pid=os.getpid(),
        exe=_port_guard._read_proc(os.getpid(), "exe"),
        cmdline=_port_guard._read_proc(os.getpid(), "cmdline"),
    )
    assert owner.exe is not None
    assert owner.cmdline is not None


def test_unreadable_proc_entries_return_none() -> None:
    assert _port_guard._read_proc(999_999_999, "exe") is None
    assert _port_guard._read_proc(999_999_999, "cmdline") is None


def test_empty_cmdline_reads_as_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Path, "read_bytes", lambda _self: b"")
    assert _port_guard._read_proc(1, "cmdline") is None
