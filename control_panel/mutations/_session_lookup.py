"""The guard both session mutations share: a real id, of a known session.

Approved by kuhy on 2026-10-22 for the sessions tab. The id must be a
canonical UUID *and* name a session the scanner found; everything else about
the session (above all its cwd) comes from the transcript, never the request.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from control_panel.mutations._types import MutationResult
from control_panel.sessions import _api

if TYPE_CHECKING:
    from control_panel.sessions._parse import Session


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
