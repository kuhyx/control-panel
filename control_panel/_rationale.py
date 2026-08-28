"""Answer "why is this enforced?" from what is already written down.

There is no structured reason field anywhere in this fleet, but the rationale
does exist -- scattered across unit-file comments, security-hardening docs,
decision logs and the ``reason`` columns of two audit files. This module reads
those, and merges them with an optional hand-written sidecar for the rules whose
"why" was never recorded anywhere.

Degrading gracefully is a hard requirement: a missing, malformed or incomplete
sidecar must yield ``None`` and a warning, never an exception and never a blank
panel. The artifacts are the floor; the sidecar is a bonus.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from control_panel import _sysroot, _systemctl, _tail
from control_panel._types import Level, Signal

if TYPE_CHECKING:
    from control_panel._manifest import ManifestEntry
    from control_panel._runner import CommandRunner

RATIONALE_DIRNAME = "rationale"
# Excerpts are bounded: a rationale panel is a summary, not a document viewer.
MAX_EXCERPT_CHARS = 1200
MAX_AUDIT_LINES = 20


@dataclass(frozen=True, slots=True)
class Artifact:
    """One piece of already-written rationale, quoted rather than summarised."""

    kind: str
    label: str
    source: str
    excerpt: str


@dataclass(frozen=True, slots=True)
class Rule:
    """A hand-written explanation for one rule, from the sidecar."""

    id: str
    why: str
    cost_of_bypass: str = ""
    ratchet: str = ""
    added: str = ""
    supersedes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Rationale:
    """Everything the dashboard can say about why a subsystem is enforced."""

    subsystem: str
    rules: tuple[Rule, ...] = ()
    artifacts: tuple[Artifact, ...] = ()
    signals: tuple[Signal, ...] = field(default_factory=tuple)


def _rationale_dir() -> Path:
    """Locate the sidecar directory next to the package."""
    return Path(__file__).resolve().parent.parent / RATIONALE_DIRNAME


def load_sidecar(subsystem_id: str, directory: Path | None = None) -> Rationale:
    """Read one sidecar file, degrading to empty on anything unexpected."""
    base = directory or _rationale_dir()
    path = base / f"{subsystem_id}.json"
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        # The common case: most subsystems' rationale lives in their artifacts.
        return Rationale(subsystem=subsystem_id)
    except (OSError, json.JSONDecodeError) as exc:
        return Rationale(
            subsystem=subsystem_id,
            signals=(
                Signal(
                    level=Level.WARN,
                    code="rationale-unreadable",
                    message=f"{path.name} could not be read: {exc}",
                ),
            ),
        )
    return _parse_sidecar(subsystem_id, raw, path)


def _parse_sidecar(subsystem_id: str, raw: object, path: Path) -> Rationale:
    """Turn a parsed sidecar document into rules, or warn and return empty."""
    if not isinstance(raw, dict) or not isinstance(raw.get("rules"), dict):
        return Rationale(
            subsystem=subsystem_id,
            signals=(
                Signal(
                    level=Level.WARN,
                    code="rationale-malformed",
                    message=f"{path.name} has no 'rules' object",
                ),
            ),
        )
    rules: list[Rule] = []
    for rule_id, body in raw["rules"].items():
        if not isinstance(body, dict):
            continue
        rules.append(
            Rule(
                id=str(rule_id),
                why=str(body.get("why", "")),
                cost_of_bypass=str(body.get("cost_of_bypass", "")),
                ratchet=str(body.get("ratchet", "")),
                added=str(body.get("added", "")),
                supersedes=tuple(str(x) for x in body.get("supersedes", ())),
            )
        )
    return Rationale(subsystem=subsystem_id, rules=tuple(rules))


def _clip(text: str) -> str:
    """Bound an excerpt so one long doc cannot dominate the payload."""
    stripped = text.strip()
    if len(stripped) <= MAX_EXCERPT_CHARS:
        return stripped
    return stripped[:MAX_EXCERPT_CHARS].rstrip() + "\n[...]"


def unit_comment(runner: CommandRunner, entry: ManifestEntry) -> list[Artifact]:
    """Extract the leading comment block of each declared unit file.

    These comments are unusually rich in this fleet -- they routinely name the
    incident that motivated a setting -- and they are frequently the only place
    a rule's reason was ever written down.
    """
    found: list[Artifact] = []
    for declared in entry.units:
        text = _systemctl.cat(runner, declared.name, declared.scope)
        comment = _leading_comment(text)
        if comment:
            found.append(
                Artifact(
                    kind="unit-comment",
                    label=declared.name,
                    source=f"systemctl {declared.scope} cat {declared.name}",
                    excerpt=_clip(comment),
                )
            )
    return found


def _leading_comment(unit_text: str) -> str:
    """Return every explanatory comment in a unit file, in order.

    Not just the leading block: in this fleet the reasoning is written *beside
    the directive it justifies*, inside the sections. ``leetcode-guard.timer``
    explains its ``Persistent=true`` flip in a comment several lines into
    ``[Timer]``, and stopping at the first ``[`` header would drop precisely the
    richest rationale on the machine.
    """
    lines: list[str] = []
    for raw in unit_text.splitlines():
        line = raw.strip()
        # `systemctl cat` prefixes each file with "# /path/to/unit"; that is
        # provenance, not rationale.
        if line.startswith("#") and not line.startswith("# /"):
            lines.append(line.lstrip("#").strip())
    return "\n".join(line for line in lines if line)


def audit_reasons(path: str, label: str) -> Artifact | None:
    """Quote the tail of an audit file that carries a free-text reason column.

    Two exist: ``/etc/shutdown-schedule-overrides.conf`` (pipe-delimited, with a
    ``reason`` field) and ``exception_audit.log``. Both are the only structured
    record of why a rule was ever relaxed.
    """
    stat = _tail.describe(path)
    if not stat.exists:
        return None
    result = _tail.tail(path, MAX_AUDIT_LINES)
    body = "\n".join(result.lines).strip()
    return Artifact(
        kind="audit-log",
        label=label,
        source=path,
        excerpt=body or "no entries recorded",
    )


def doc_excerpt(path: str, label: str) -> Artifact | None:
    """Quote the opening of a policy document, if it is present."""
    resolved = (
        _sysroot.user_path(path[2:])
        if path.startswith("~/")
        else _sysroot.sysroot_path(path)
    )
    try:
        text = resolved.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    return Artifact(kind="doc", label=label, source=path, excerpt=_clip(text))


def to_payload(rationale: Rationale) -> dict[str, Any]:
    """Render a :class:`Rationale` as the ``/api/why/<id>`` body."""
    return asdict(rationale)


def build(runner: CommandRunner, entry: ManifestEntry) -> Rationale:
    """Assemble both halves of the answer for one subsystem.

    Artifacts first and unconditionally: they are what already exists, so the
    panel is useful before a single sidecar has been written. The sidecar then
    supplies the rules whose reason was never recorded anywhere.
    """
    sidecar = load_sidecar(entry.id)
    artifacts: list[Artifact] = list(unit_comment(runner, entry))
    for source in entry.docs:
        found = doc_excerpt(source.path, source.label)
        if found is not None:
            artifacts.append(found)
    for source in entry.audits:
        found = audit_reasons(source.path, source.label)
        if found is not None:
            artifacts.append(found)
    return Rationale(
        subsystem=entry.id,
        rules=sidecar.rules,
        artifacts=tuple(artifacts),
        signals=sidecar.signals,
    )
