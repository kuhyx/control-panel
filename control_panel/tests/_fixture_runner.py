"""A CommandRunner backed by canned output, plus real captured systemd data.

The fixtures below are *real* output from the machine this was built on, so the
tests assert on the genuine anomalies (a never-installed phone timer, a
disabled budget timer, a broken code-tunnel unit) by name rather than on
invented ones.
"""

from __future__ import annotations

import json

from control_panel._runner import CommandResult


class FakeRunner:
    """Return canned results, and record every argv it was asked to run."""

    def __init__(self, responses: dict[tuple[str, ...], CommandResult]) -> None:
        """Store the canned responses keyed by exact argv."""
        self.responses = responses
        self.calls: list[tuple[str, ...]] = []

    def run(self, argv: tuple[str, ...], timeout: float = 10.0) -> CommandResult:
        """Return the canned result for ``argv``, or a non-zero miss."""
        del timeout
        self.calls.append(argv)
        if argv in self.responses:
            return self.responses[argv]
        return CommandResult(argv=argv, returncode=1, stdout="", stderr="no fixture")


def ok(argv: tuple[str, ...], stdout: str) -> CommandResult:
    """Build a successful result."""
    return CommandResult(argv=argv, returncode=0, stdout=stdout, stderr="")


def unit_files_json(rows: list[tuple[str, str, str]]) -> str:
    """Render rows as `systemctl list-unit-files --output=json` output."""
    return json.dumps([{"unit_file": n, "state": s, "preset": p} for n, s, p in rows])


def timers_json(rows: list[tuple[str, int | None, str]]) -> str:
    """Render rows as `systemctl list-timers --output=json` output."""
    return json.dumps(
        [
            {"unit": u, "next": nxt, "last": 1, "passed": 0, "activates": act}
            for u, nxt, act in rows
        ]
    )


def show_blocks(units: list[dict[str, str]]) -> str:
    """Render property blocks as `systemctl show a b c` emits them."""
    return "\n\n".join("\n".join(f"{k}={v}" for k, v in unit.items()) for unit in units)
