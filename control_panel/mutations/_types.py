"""The shape every mutation answers with.

One type for every knob (five since kuhy approved the two session mutations
on 2026-10-22), because the interesting field is the same in
every case: what the underlying script said when it refused. The dashboard
never decides whether a change is allowed -- it relays.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class MutationResult:
    """The outcome of one attempted change.

    ``refused`` is distinct from ``ok``: a refusal is the ratchet working, and
    should be rendered as the guard doing its job rather than as an error. A
    failure is the machinery being broken.
    """

    ok: bool
    refused: bool
    summary: str
    # Relayed verbatim, never paraphrased: the script's own wording is the
    # explanation, and rewording it would be the dashboard inventing policy.
    stdout: str = ""
    stderr: str = ""
    argv: tuple[str, ...] = ()

    @classmethod
    def refusal(
        cls, summary: str, stderr: str, argv: tuple[str, ...] = ()
    ) -> MutationResult:
        """Build the result for a change the underlying guard rejected."""
        return cls(ok=False, refused=True, summary=summary, stderr=stderr, argv=argv)

    @classmethod
    def failure(cls, summary: str, stderr: str = "") -> MutationResult:
        """Build the result for a change that could not be attempted."""
        return cls(ok=False, refused=False, summary=summary, stderr=stderr)

    @classmethod
    def success(
        cls, summary: str, stdout: str = "", argv: tuple[str, ...] = ()
    ) -> MutationResult:
        """Build the result for a change that landed."""
        return cls(ok=True, refused=False, summary=summary, stdout=stdout, argv=argv)


def to_payload(result: MutationResult) -> dict[str, Any]:
    """Render a :class:`MutationResult` as a JSON body."""
    return asdict(result)
