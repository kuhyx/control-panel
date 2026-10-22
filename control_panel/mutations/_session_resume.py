"""Reopen a Claude Code session in a new terminal window.

Approved by kuhy on 2026-10-22 for the sessions tab, as a second narrow
exception beside :mod:`._restart`: it *starts* a unit, but only a transient
``systemd-run --user --collect`` scope around a terminal, never a declared
unit, so it cannot arm or disarm anything. The terminal runs in its own unit
so that restarting ``control-panel-web.service`` does not kill it.

Safety: the id is a canonical UUID of a session the scanner found, the cwd is
read from that session's transcript, and the command is an argv tuple. The
only request-derived text inside the ``zsh -c`` string is the id, which
:func:`build_argv` re-checks rather than trusting its caller.
"""

from __future__ import annotations

import os
import time
from typing import TYPE_CHECKING

from control_panel import _sysroot
from control_panel.mutations._session_lookup import known_session
from control_panel.mutations._types import MutationResult
from control_panel.sessions import _api

if TYPE_CHECKING:
    from control_panel._runner import CommandRunner

# systemd-run returns once the unit has started; it never waits on the window.
TIMEOUT = 15.0
SHOW_ENV = ("systemctl", "--user", "show-environment")
DEFAULT_DISPLAY = ":0"


# The clock, as a seam so tests get a fixed unit name.
now = time.time


def _display_env(runner: CommandRunner) -> tuple[str, str]:
    """DISPLAY and XAUTHORITY from the user manager, with sane defaults.

    The web service's own environment may lack both; the user manager has
    whatever the X session imported into it.
    """
    env: dict[str, str] = {}
    result = runner.run(SHOW_ENV)
    if result.ok:
        for line in result.stdout.splitlines():
            key, sep, value = line.partition("=")
            if sep:
                env[key] = value
    home = os.environ.get("HOME", "").rstrip("/")
    # systemd-run does not expand "~", so the default is spelled out.
    return (
        env.get("DISPLAY") or DEFAULT_DISPLAY,
        env.get("XAUTHORITY") or f"{home}/.Xauthority",
    )


def build_argv(
    session_id: str, cwd: str, display: str, xauthority: str, epoch: int
) -> tuple[str, ...]:
    """The launch command. Raises ValueError unless the id is canonical."""
    if _api.canonical_id(session_id) != session_id:
        msg = f"refusing a non-canonical session id: {session_id!r}"
        raise ValueError(msg)
    return (
        "systemd-run",
        "--user",
        "--collect",
        f"--unit=claude-resume-{session_id[:8]}-{epoch}",
        f"--setenv=DISPLAY={display}",
        f"--setenv=XAUTHORITY={xauthority}",
        "terminator",
        f"--working-directory={cwd}",
        "-x",
        "zsh",
        "-lic",
        # Drop to a shell afterwards so the window survives /exit.
        f"claude --resume {session_id}; exec zsh -i",
    )


def apply(runner: CommandRunner, body: object) -> MutationResult:
    """Open a terminal resuming one known session in its own directory."""
    session = known_session(body)
    if isinstance(session, MutationResult):
        return session
    if not session.cwd or not _sysroot.sysroot_path(session.cwd).is_dir():
        return MutationResult.failure(
            f"{session.cwd or 'The session directory'} no longer exists.",
            stderr="claude --resume only finds a session from its own directory.",
        )
    display, xauthority = _display_env(runner)
    argv = build_argv(session.id, session.cwd, display, xauthority, int(now()))
    result = runner.run(argv, timeout=TIMEOUT)
    if result.ok:
        return MutationResult.success(
            f"Resuming {session.title or session.id} in a new terminal.",
            stdout=result.stdout.strip()[-2000:],
            argv=argv,
        )
    return MutationResult.failure(
        "Could not open a terminal.",
        stderr=(result.error or result.stderr.strip())[-4000:],
    )
