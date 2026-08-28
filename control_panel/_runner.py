"""Command seam: every subprocess this package spawns goes through here.

You cannot fake ``systemctl`` through a filesystem prefix the way you can fake
``/etc``, which is why commands get their own seam instead of sharing
:mod:`control_panel._sysroot`. Tests inject a ``FakeRunner`` backed by real
captured output.

Every call is ``shell=False`` with an explicit timeout and ``check=False``:
a dashboard that hangs because one subsystem's CLI wedged is worse than a
dashboard that reports that subsystem as UNKNOWN.
"""

from __future__ import annotations

from dataclasses import dataclass
import subprocess
from typing import Protocol

DEFAULT_TIMEOUT = 10.0


@dataclass(frozen=True, slots=True)
class CommandResult:
    """The outcome of one command, including the failures.

    ``returncode`` is ``None`` when the command never ran to completion --
    timed out, or the binary was missing. Callers distinguish "ran and said no"
    from "could not be asked" on that field.
    """

    argv: tuple[str, ...]
    returncode: int | None
    stdout: str
    stderr: str
    timed_out: bool = False
    error: str | None = None

    @property
    def ok(self) -> bool:
        """True when the command ran and exited zero."""
        return self.returncode == 0


class CommandRunner(Protocol):
    """The seam every collector depends on instead of ``subprocess``."""

    def run(
        self, argv: tuple[str, ...], timeout: float = DEFAULT_TIMEOUT
    ) -> CommandResult:
        """Execute ``argv`` and return its outcome, never raising."""
        ...  # pragma: no cover


class SubprocessRunner:
    """The production :class:`CommandRunner`, backed by ``subprocess.run``."""

    def run(
        self, argv: tuple[str, ...], timeout: float = DEFAULT_TIMEOUT
    ) -> CommandResult:
        """Execute ``argv``, converting every failure mode into a result."""
        try:
            completed = subprocess.run(
                list(argv),
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
                shell=False,
            )
        except subprocess.TimeoutExpired:
            return CommandResult(
                argv=argv,
                returncode=None,
                stdout="",
                stderr="",
                timed_out=True,
                error=f"timed out after {timeout}s",
            )
        except (OSError, subprocess.SubprocessError) as exc:
            return CommandResult(
                argv=argv, returncode=None, stdout="", stderr="", error=str(exc)
            )
        return CommandResult(
            argv=argv,
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
