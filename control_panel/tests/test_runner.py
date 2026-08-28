from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

from control_panel._runner import CommandResult, SubprocessRunner

if TYPE_CHECKING:
    import pytest


def test_successful_command_is_ok() -> None:
    result = SubprocessRunner().run(("printf", "hello"))
    assert result.ok
    assert result.stdout == "hello"


def test_non_zero_exit_is_not_ok() -> None:
    result = SubprocessRunner().run(("false",))
    assert not result.ok
    assert result.returncode == 1


def test_missing_binary_becomes_a_result_not_an_exception() -> None:
    result = SubprocessRunner().run(("definitely-not-a-real-binary-xyz",))
    assert result.returncode is None
    assert result.error is not None
    assert not result.ok


def test_timeout_becomes_a_result(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*_args: object, **_kwargs: object) -> None:
        raise subprocess.TimeoutExpired(cmd="sleep", timeout=0.01)

    monkeypatch.setattr(subprocess, "run", boom)
    result = SubprocessRunner().run(("sleep", "5"), timeout=0.01)
    assert result.timed_out
    assert result.returncode is None
    assert not result.ok


def test_command_result_ok_property() -> None:
    assert CommandResult(argv=(), returncode=0, stdout="", stderr="").ok
    assert not CommandResult(argv=(), returncode=None, stdout="", stderr="").ok
