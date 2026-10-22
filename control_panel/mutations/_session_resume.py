"""Reopen Claude Code sessions in new terminal windows, at most five at once.

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
from control_panel.mutations._session_lookup import is_bulk, known_sessions, plural
from control_panel.mutations._types import MutationResult
from control_panel.sessions import _api

if TYPE_CHECKING:
    from control_panel._runner import CommandRunner
    from control_panel.sessions._parse import Session

# systemd-run returns once the unit has started; it never waits on the window.
TIMEOUT = 15.0
# One click opens at most this many windows; more is a refusal, not a queue.
MAX_BULK = 5
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


def _missing_dirs(sessions: list[Session]) -> MutationResult | None:
    """Refuse to launch anything if any session's directory is gone."""
    missing = [
        s.cwd or "The session directory"
        for s in sessions
        if not s.cwd or not _sysroot.sysroot_path(s.cwd).is_dir()
    ]
    if not missing:
        return None
    return MutationResult.failure(
        f"{', '.join(missing)} no longer exists.",
        stderr="claude --resume only finds a session from its own directory.",
    )


def _over_cap(body: object) -> MutationResult | None:
    """Refuse a bulk request naming more sessions than one click should open."""
    raw = body.get("ids") if isinstance(body, dict) else None
    if not isinstance(raw, list) or len(raw) <= MAX_BULK:
        return None
    return MutationResult.refusal(
        f"At most {MAX_BULK} sessions can be resumed at once.",
        stderr=f"Got {len(raw)} ids; no terminal was opened.",
    )


def apply(runner: CommandRunner, body: object) -> MutationResult:
    """Open a terminal per known session, each in its own directory."""
    refused = _over_cap(body)
    if refused is not None:
        return refused
    sessions = known_sessions(body)
    if isinstance(sessions, MutationResult):
        return sessions
    refused = _missing_dirs(sessions)
    if refused is not None:
        return refused
    display, xauthority = _display_env(runner)
    epoch = int(now())
    opened: list[tuple[str, tuple[str, ...], str]] = []
    for session in sessions:
        argv = build_argv(session.id, session.cwd, display, xauthority, epoch)
        result = runner.run(argv, timeout=TIMEOUT)
        if not result.ok:
            summary = "Could not open a terminal."
            if is_bulk(body):
                summary = (
                    f"Opened {len(opened)} of {len(sessions)} terminals; "
                    f"could not open one for {session.id}."
                )
            return MutationResult.failure(
                summary, stderr=(result.error or result.stderr.strip())[-4000:]
            )
        opened.append((session.id, argv, result.stdout.strip()))
    if is_bulk(body):
        # One payload carries one argv; a bulk launch reports per-id lines.
        return MutationResult.success(
            f"Resuming {plural(len(sessions))} in new terminals.",
            stdout="\n".join(f"{sid}: {out}" for sid, _, out in opened)[-2000:],
        )
    _, argv, out = opened[0]
    return MutationResult.success(
        f"Resuming {sessions[0].title or sessions[0].id} in a new terminal.",
        stdout=out[-2000:],
        argv=argv,
    )
