"""Make the curfew stricter. Never looser -- and never by deciding so here.

This module contains **no comparison of old against new**. That comparison
lives in ``screen-locker``'s ``adjust_shutdown_schedule.sh``, which is what the
guard-lib path unit, the sudoers entry and the sick-day flow all already trust.
A second implementation here would be a second thing to get wrong, and worse,
it would be a *new bypass*: the dashboard could then permit something the
script would have refused.

So the only judgement this file makes is "these are three integers", and the
answer to everything else is whatever the script's exit status says.

``--restore`` is never passed. That flag exists for the workout reward, which
legitimately loosens the schedule; handing a web UI the flag that turns the
ratchet off would defeat the point of having one.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from control_panel.mutations import _repos
from control_panel.mutations._types import MutationResult

if TYPE_CHECKING:
    from control_panel._runner import CommandRunner

SCRIPT = "screen_locker/adjust_shutdown_schedule.sh"
REPO = "screen-locker"
MAX_HOUR = 23
# The script takes a while only because sudo may prompt; it never should here,
# since kuhy has NOPASSWD, but a hung sudo must not hang the dashboard.
TIMEOUT = 20.0


def _parse_hours(raw: object) -> tuple[int, int, int] | None:
    """Read three hours out of the request body, or None if it is not that."""
    if not isinstance(raw, dict):
        return None
    try:
        hours = (
            int(raw["mon_wed_hour"]),
            int(raw["thu_sun_hour"]),
            int(raw["morning_end_hour"]),
        )
    except KeyError, TypeError, ValueError:
        return None
    if any(hour < 0 or hour > MAX_HOUR for hour in hours):
        return None
    return hours


def apply(runner: CommandRunner, body: object) -> MutationResult:
    """Ask the ratchet script to tighten the curfew."""
    hours = _parse_hours(body)
    if hours is None:
        return MutationResult.failure(
            "Expected mon_wed_hour, thu_sun_hour and morning_end_hour "
            f"as integers in 0..{MAX_HOUR}."
        )

    repo = _repos.locate(runner, REPO)
    if repo.path is None:
        return MutationResult.failure(f"Cannot find the {REPO} checkout: {repo.detail}")
    script = repo.path / SCRIPT
    if not script.is_file():
        return MutationResult.failure(f"{script} does not exist")

    argv = ("/usr/bin/sudo", str(script), *(str(hour) for hour in hours))
    result = runner.run(argv, timeout=TIMEOUT)
    mon_wed, thu_sun, morning_end = hours
    asked = f"Mon-Wed {mon_wed}:00, Thu-Sun {thu_sun}:00, morning end {morning_end}:00"
    if result.ok:
        return MutationResult.success(
            f"Curfew tightened to {asked}.", stdout=result.stdout, argv=argv
        )
    if result.returncode is None:
        return MutationResult.failure(
            f"The ratchet script did not run: {result.error}", stderr=result.stderr
        )
    # Exit 1 is the ratchet refusing, which is the guard working. Its stderr
    # already explains which value moved the wrong way and why.
    return MutationResult.refusal(
        f"Refused: {asked} is not stricter than the current schedule.",
        stderr=result.stderr.strip(),
        argv=argv,
    )
