"""Typed reads of systemd's own view, via ``systemctl --output=json``.

All four query shapes here were captured from the live machine before being
written down. In particular ``list-timers`` and ``list-unit-files`` both
support ``--output=json``, so this module never does the ``" n/a "`` substring
parsing that ``screen-locker``'s ``check_enforcement_armed.py`` had to resort
to against text output.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import TYPE_CHECKING, Any

from control_panel._types import Scope

if TYPE_CHECKING:
    from control_panel._runner import CommandRunner

# Properties fetched for every unit. `systemctl show` silently omits properties
# that do not apply to a unit type (a .timer has no ExecStart), so the parser
# must treat "absent" and "empty" as the same thing.
SHOW_PROPERTIES = (
    "Id",
    "LoadState",
    "UnitFileState",
    "UnitFilePreset",
    "ActiveState",
    "SubState",
    "Result",
    "ExecStart",
    "FragmentPath",
    "NextElapseUSecRealtime",
    "LastTriggerUSec",
    "Unit",
    # TriggeredBy is what makes arming delegation computable instead of
    # declared: a service pulled in by a timer is `disabled` by design, and
    # systemd already knows which timer arms it.
    "TriggeredBy",
    "WantedBy",
)


def _scope_args(scope: Scope) -> tuple[str, ...]:
    """Return the ``--user`` flag for user-scope queries, nothing otherwise."""
    return ("--user",) if scope is Scope.USER else ()


@dataclass(frozen=True, slots=True)
class UnitFile:
    """One row of ``systemctl list-unit-files --output=json``."""

    name: str
    state: str
    preset: str


@dataclass(frozen=True, slots=True)
class TimerRow:
    """One row of ``systemctl list-timers --all --output=json``.

    ``next`` is ``null`` for a timer that is installed but not scheduled --
    which is precisely how ``kuhytrack-budget.timer`` presents.
    """

    unit: str
    next_elapse: int | None
    last_trigger: int | None
    activates: str | None


def _load_json_array(stdout: str) -> list[dict[str, Any]]:
    """Parse a JSON array of objects, returning ``[]`` on any malformation."""
    try:
        parsed = json.loads(stdout)
    except (json.JSONDecodeError, ValueError):
        return []
    if not isinstance(parsed, list):
        return []
    return [row for row in parsed if isinstance(row, dict)]


def list_unit_files(runner: CommandRunner, scope: Scope) -> dict[str, UnitFile]:
    """Return every installed service/timer/path unit, keyed by unit name."""
    argv = (
        "systemctl",
        *_scope_args(scope),
        "list-unit-files",
        "--no-pager",
        "--output=json",
        "--type=service,timer,path",
    )
    result = runner.run(argv)
    if not result.ok:
        return {}
    files: dict[str, UnitFile] = {}
    for row in _load_json_array(result.stdout):
        name = row.get("unit_file")
        if not isinstance(name, str):
            continue
        files[name] = UnitFile(
            name=name,
            state=str(row.get("state") or ""),
            preset=str(row.get("preset") or ""),
        )
    return files


def list_timers(runner: CommandRunner, scope: Scope) -> dict[str, TimerRow]:
    """Return every timer systemd is tracking, keyed by unit name."""
    argv = (
        "systemctl",
        *_scope_args(scope),
        "list-timers",
        "--all",
        "--no-pager",
        "--output=json",
    )
    result = runner.run(argv)
    if not result.ok:
        return {}
    timers: dict[str, TimerRow] = {}
    for row in _load_json_array(result.stdout):
        unit = row.get("unit")
        if not isinstance(unit, str):
            continue
        timers[unit] = TimerRow(
            unit=unit,
            next_elapse=_as_int(row.get("next")),
            last_trigger=_as_int(row.get("last")),
            activates=row.get("activates")
            if isinstance(row.get("activates"), str)
            else None,
        )
    return timers


def _as_int(value: object) -> int | None:
    """Coerce a JSON number to ``int``, mapping null/garbage/zero to ``None``.

    systemd emits ``0`` for a timer that has never fired, which means the same
    thing as ``null`` here and should not render as an epoch in 1970.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value or None


def list_bad_units(runner: CommandRunner, scope: Scope) -> frozenset[str]:
    """Return unit names systemd reports as ``bad`` (unparsable unit file)."""
    argv = (
        "systemctl",
        *_scope_args(scope),
        "list-unit-files",
        "--state=bad",
        "--no-pager",
        "--output=json",
    )
    result = runner.run(argv)
    if not result.ok:
        return frozenset()
    names = {
        row["unit_file"]
        for row in _load_json_array(result.stdout)
        if isinstance(row.get("unit_file"), str)
    }
    return frozenset(names)


def show_many(
    runner: CommandRunner, units: tuple[str, ...], scope: Scope
) -> dict[str, dict[str, str]]:
    """Return ``systemctl show`` properties for many units in ONE fork.

    ``systemctl show a b c`` emits one blank-line-separated property block per
    unit, in argument order. Batching matters: the fleet declares ~46 units, and
    a fork each turns one page refresh into a visible stall on a machine whose
    own polling rules forbid exactly that.

    Blocks are matched back to units by their ``Id`` property rather than by
    position, because a unit named on the command line by an alias comes back
    under its canonical Id. Units systemd knows nothing about still get a block,
    so the caller sees ``LoadState=not-found`` rather than a missing key.
    """
    if not units:
        return {}
    argv = (
        "systemctl",
        *_scope_args(scope),
        "show",
        *units,
        "--no-pager",
        f"-p{','.join(SHOW_PROPERTIES)}",
    )
    result = runner.run(argv, timeout=30.0)
    if not result.ok:
        return {}
    blocks = result.stdout.split("\n\n")
    parsed: dict[str, dict[str, str]] = {}
    for block, requested in zip(blocks, units, strict=False):
        props = _parse_block(block)
        # Prefer the canonical Id, but always record the requested name too so
        # an alias or template instance is still findable by what we asked for.
        parsed[requested] = props
        canonical = props.get("Id")
        if canonical:
            parsed.setdefault(canonical, props)
    return parsed


def _parse_block(block: str) -> dict[str, str]:
    """Parse one ``KEY=value`` property block into a flat dict."""
    props: dict[str, str] = {}
    for line in block.splitlines():
        key, sep, value = line.partition("=")
        if sep:
            props[key] = value
    return props


def cat(runner: CommandRunner, unit: str, scope: Scope) -> str:
    """Return the verbatim unit file text, or ``""`` when unreadable.

    Used by the rationale panel: the leading comment block of a unit file is
    often the only written record of *why* a setting is what it is.
    """
    argv = ("systemctl", *_scope_args(scope), "cat", unit, "--no-pager")
    result = runner.run(argv)
    return result.stdout if result.ok else ""
