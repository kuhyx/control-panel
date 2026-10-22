"""The guard every session mutation shares: real ids, of known sessions.

Approved by kuhy on 2026-10-22 for the sessions tab. An id must be a
canonical UUID *and* name a session the scanner found; everything else about
the session (above all its cwd) comes from the transcript, never the request.

A body names one session as ``{"id"}`` or several as ``{"ids": [...]}``. A
bulk request is all-or-nothing: one bad id refuses the lot, naming every bad
id, so nothing is ever half-applied because of a typo.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from control_panel.mutations._types import MutationResult
from control_panel.sessions import _api

if TYPE_CHECKING:
    from control_panel.sessions._parse import Session

# How many bad ids the one-line summary spells out; stderr lists them all.
_SUMMARY_NAMES = 5


def known_session(body: object) -> Session | MutationResult:
    """Return the session a request names, or the result refusing it."""
    if not isinstance(body, dict):
        return MutationResult.failure("Expected a JSON object.")
    raw = body.get("id")
    session_id = _api.canonical_id(raw)
    if session_id is None:
        return MutationResult.refusal(
            "Not a session id.",
            stderr=f"Expected a lowercase hyphenated UUID, got {str(raw)[:80]!r}.",
        )
    session = _api.find(session_id)
    if session is None:
        return MutationResult.refusal(
            f"No interactive session {session_id}.",
            stderr="Only sessions listed on the Sessions tab can be acted on.",
        )
    return session


def is_bulk(body: object) -> bool:
    """Whether a body uses the ``ids`` list rather than a single ``id``."""
    return isinstance(body, dict) and "ids" in body


def _bad_name(raw: object) -> str:
    """How a rejected id is shown: known-shape ids bare, anything else repr'd."""
    session_id = _api.canonical_id(raw)
    return session_id if session_id is not None else repr(raw)[:40]


def _refuse_bad(bad: list[str]) -> MutationResult:
    """Refuse a whole bulk request, naming the ids that sank it."""
    shown = ", ".join(bad[:_SUMMARY_NAMES])
    if len(bad) > _SUMMARY_NAMES:
        shown += f" (+{len(bad) - _SUMMARY_NAMES} more)"
    return MutationResult.refusal(
        f"Nothing done: not known sessions: {shown}.",
        stderr="Not interactive sessions on the Sessions tab:\n" + "\n".join(bad),
    )


def known_sessions(body: object) -> list[Session] | MutationResult:
    """Return every session a request names, in order, or the refusal.

    One scan answers the whole list, so a bulk request costs what one does.
    Duplicates collapse, so a repeated id cannot be acted on twice.
    """
    if not isinstance(body, dict) or "ids" not in body:
        single = known_session(body)
        return single if isinstance(single, MutationResult) else [single]
    raw = body["ids"]
    if "id" in body or not isinstance(raw, list) or not raw:
        return MutationResult.failure(
            "Expected either 'id' or a non-empty list 'ids', not both."
        )
    found = _api.SCANNER.scan(_api.projects_dir())[0]
    sessions: dict[str, Session] = {}
    bad: list[str] = []
    for item in raw:
        session_id = _api.canonical_id(item)
        session = found.get(session_id) if session_id is not None else None
        if session is None:
            bad.append(_bad_name(item))
        else:
            sessions.setdefault(session.id, session)
    if bad:
        return _refuse_bad(bad)
    return list(sessions.values())


def plural(count: int, noun: str = "session") -> str:
    """``1 session`` / ``3 sessions``."""
    return f"{count} {noun}{'' if count == 1 else 's'}"
