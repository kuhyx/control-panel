"""Locate the extracted repos whose scripts the mutations shell out to.

The fleet was extracted out of ``testsAndMisc`` one repo at a time, and
``linux_configuration/lib/extracted_repos.sh`` already answers "where is
screen-locker?" -- including the ``*_DIR`` override vars for a non-standard
checkout. Reusing it means a future extraction moves one file, not this one.

Deliberately **not** ``require_extracted_repo``: that helper *clones* a missing
repo, and cloning is a write nobody asked this dashboard to perform.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from control_panel import _sysroot

if TYPE_CHECKING:
    from pathlib import Path

    from control_panel._runner import CommandRunner

RESOLVER = "~/src/testsAndMisc/linux_configuration/lib/extracted_repos.sh"


@dataclass(frozen=True, slots=True)
class RepoPath:
    """Where a repo is, and whether it is actually there."""

    name: str
    path: Path | None
    detail: str = ""


def _fallback(name: str) -> Path:
    """Return the conventional checkout location under the user's home."""
    return _sysroot.user_path(name)


def locate(runner: CommandRunner, name: str) -> RepoPath:
    """Resolve one extracted repo, falling back to ``~/<name>``.

    The resolver is a shell function, so it has to be sourced rather than
    executed. When it is unavailable -- a fresh machine, or a test tree -- the
    convention it encodes is still right, so the fallback is the same answer by
    a cheaper route rather than a failure.
    """
    script = _sysroot.user_path(RESOLVER.removeprefix("~/"))
    if script.is_file():
        result = runner.run(
            (
                "bash",
                "-c",
                f'source "{script}"; extracted_repo_dir "{name}"',
            )
        )
        resolved = result.stdout.strip()
        if result.ok and resolved:
            path = _sysroot.sysroot_path(resolved)
            if path.is_dir():
                return RepoPath(name=name, path=path)
            return RepoPath(name=name, path=None, detail=f"{resolved} does not exist")
    guess = _fallback(name)
    if guess.is_dir():
        return RepoPath(name=name, path=guess)
    return RepoPath(name=name, path=None, detail=f"{guess} does not exist")
