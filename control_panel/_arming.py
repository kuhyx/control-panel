"""Decide whether a declared unit will actually fire. Pure function, no I/O.

Isolating this from the adapters is the single decision that makes 100% branch
coverage cheap here: every rule below is exercised by a parametrised table with
no filesystem and no subprocess. Rules are evaluated top-down, first match wins,
and each one carries the reason it fired so the UI can explain itself.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from control_panel._types import Arming, UnitRecord, UnitState

if TYPE_CHECKING:
    from control_panel._manifest import ManifestUnit
    from control_panel._systemctl import TimerRow, UnitFile

# Unit-file states from which a service will still be started by systemd.
# `static` counts: it has no [Install] section because something else pulls it
# in, which is a deliberate pattern in this fleet (leetcode-guard.service says
# so in its own comments), not a sign of being disabled.
ARMED_SERVICE_STATES = frozenset({"enabled", "enabled-runtime", "static"})
ARMED_TIMER_STATES = frozenset({"enabled", "enabled-runtime"})
# LoadState values that mean systemd could not use the unit at all.
BROKEN_LOAD_STATES = frozenset({"error", "not-found", "masked"})


@dataclass(frozen=True, slots=True)
class Observation:
    """Everything observed about one declared unit, ready to be judged.

    Bundled rather than passed as eight positional arguments so the decision
    functions stay readable and no caller can transpose two booleans.
    """

    declared: ManifestUnit
    unit_file: UnitFile | None
    timer: TimerRow | None = None
    props: dict[str, str] = field(default_factory=dict)
    is_bad: bool = False
    triggers: tuple[str, ...] = ()
    # Tri-state. ``None`` means the units that activate this one are not in the
    # manifest, so their arming is unknown -- defaulting an undeclared trigger
    # to "unarmed" would invent failures.
    peers_armed: bool | None = None
    exec_start_exists: bool | None = None

    @property
    def state_note(self) -> str:
        """Describe the unit-file state, for use in a reason line."""
        if self.unit_file is None:
            return "not installed"
        return (
            f"unit file state is {self.unit_file.state!r} "
            f"(preset {self.unit_file.preset!r})"
        )


def exec_start_binary(props: dict[str, str]) -> str | None:
    """Extract the executable path from a ``systemctl show`` ExecStart value.

    ExecStart is rendered as ``{ path=/usr/bin/foo ; argv[]=... }``. The
    ``path=`` field is the one that matters: an ExecStart naming a script that
    no longer exists is how the phone-sync rot would have been caught.
    """
    raw = props.get("ExecStart", "")
    marker = "path="
    start = raw.find(marker)
    if start == -1:
        return None
    tail = raw[start + len(marker) :].lstrip()
    binary = tail.split(" ", 1)[0].strip().rstrip(";")
    return binary or None


def delegates_to(
    declared: ManifestUnit, props: dict[str, str], activated_by: tuple[str, ...] = ()
) -> tuple[str, ...]:
    """Return the units whose arming decides this one's, if any.

    ``activated_by`` -- built by the caller from declared *timers'* ``Unit=``
    property -- is authoritative and comes first. ``TriggeredBy`` is only a
    supplement, because it is a **runtime** relationship: a disabled timer is
    not loaded, so systemd reports its target's ``TriggeredBy`` as empty. That
    made ``kuhytrack-budget.service`` read ARMED (``static``) while the timer
    that fires it was disabled -- precisely the false-negative this dashboard
    exists to catch.

    Timers never delegate, so the chain terminates in one hop.
    """
    if declared.kind == "timer" or declared.retired is not None:
        return ()
    return (
        activated_by
        or tuple(props.get("TriggeredBy", "").split())
        or declared.arming_lives_on
    )


def _decide_timer(obs: Observation, unit_file: UnitFile) -> tuple[Arming, list[str]]:
    """Decide a timer's arming, separating "not enabled" from "not scheduled".

    The distinction is load-bearing. ``kuhytrack-budget.timer`` is disabled and
    unknown to systemd -- genuinely unarmed. ``pc-startup-monitor.timer`` is
    enabled and tracked, but its next elapse is null because the oneshot it
    activates is still ``active (exited)``, and systemd will not re-arm a timer
    whose unit has not deactivated. Both stop firing; only the second one looks
    healthy to ``systemctl is-enabled``, so it has to say why.
    """
    if unit_file.state not in ARMED_TIMER_STATES:
        return Arming.UNARMED, [
            obs.state_note,
            "not enabled, so systemd never arms it",
        ]
    if obs.timer is None:
        return Arming.UNARMED, [
            obs.state_note,
            "absent from `systemctl list-timers`",
        ]
    if obs.timer.next_elapse is None:
        return Arming.DEGRADED, [
            obs.state_note,
            "enabled and tracked, but systemd has scheduled no next elapse",
            f"a timer will not re-arm while {obs.timer.activates or 'its unit'} is "
            "still active -- check for a RemainAfterExit oneshot that never "
            "deactivated",
        ]
    return Arming.ARMED, [f"{unit_file.state}, next elapse scheduled"]


def _decide_service(obs: Observation, unit_file: UnitFile) -> tuple[Arming, list[str]]:
    """Decide a service's arming, delegating when something else activates it.

    A service pulled in by a timer or a target is ``disabled`` by design --
    ``auto-system-update.service`` and ``workout-locker.service`` both are.
    Judging such a service on its own unit-file state would report the entire
    timer-driven half of the fleet as unarmed.
    """
    if obs.triggers:
        named = ", ".join(obs.triggers)
        if obs.peers_armed is None:
            return Arming.UNKNOWN, [
                f"activated by {named}, which is not declared in the manifest, "
                "so its arming could not be established"
            ]
        if obs.peers_armed:
            return Arming.ARMED, [f"activated by {named}"]
        return Arming.UNARMED, [f"nothing that activates it is armed: {named}"]
    if obs.declared.login_oneshot:
        return Arming.ARMED, ["login one-shot, started by its target at session start"]
    if unit_file.state in ARMED_SERVICE_STATES:
        return Arming.ARMED, [unit_file.state]
    return Arming.UNARMED, [obs.state_note]


def _decide(obs: Observation) -> tuple[Arming, list[str]]:
    """Return the arming state and the reasons that produced it."""
    retired = obs.declared.retired
    if retired is not None:
        why = [f"declared retired, superseded by {retired.superseded_by}"]
        if obs.unit_file is not None and obs.unit_file.state in ARMED_TIMER_STATES:
            why.append(f"but still {obs.unit_file.state} in systemd")
        return Arming.RETIRED, why

    unit_file = obs.unit_file
    if unit_file is None:
        return Arming.NOT_INSTALLED, [
            "declared in the fleet manifest",
            "absent from `systemctl list-unit-files`",
        ]

    load_state = obs.props.get("LoadState", "")
    if obs.is_bad or load_state in BROKEN_LOAD_STATES:
        return Arming.BAD, [
            obs.state_note,
            f"LoadState={load_state or 'unknown'}",
        ]

    if obs.declared.kind == "timer":
        return _decide_timer(obs, unit_file)
    return _decide_service(obs, unit_file)


def evaluate(obs: Observation) -> UnitRecord:
    """Build the full :class:`UnitRecord` for one observed unit."""
    state, reasons = _decide(obs)
    if obs.declared.why_it_matters:
        reasons.append(obs.declared.why_it_matters)
    if obs.exec_start_exists is False:
        reasons.append("ExecStart names a path that does not exist")
    timer = obs.timer
    return UnitRecord(
        name=obs.declared.name,
        scope=obs.declared.scope,
        arming=state,
        installed=obs.unit_file is not None,
        state=UnitState(
            unit_file_state=obs.unit_file.state if obs.unit_file else None,
            preset=obs.unit_file.preset if obs.unit_file else None,
            active_state=obs.props.get("ActiveState") or None,
            sub_state=obs.props.get("SubState") or None,
            result=obs.props.get("Result") or None,
            next_elapse=str(timer.next_elapse) if timer and timer.next_elapse else None,
            last_trigger=(
                str(timer.last_trigger) if timer and timer.last_trigger else None
            ),
            exec_start=exec_start_binary(obs.props),
            exec_start_exists=obs.exec_start_exists,
        ),
        declared_retired=obs.declared.retired is not None,
        login_oneshot=obs.declared.login_oneshot,
        arming_reason=tuple(reasons),
    )
