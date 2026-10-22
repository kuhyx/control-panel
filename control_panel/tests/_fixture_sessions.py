"""Synthetic Claude Code transcripts, shaped like the real ``*.jsonl`` records.

Field names and record order are copied from transcripts on this machine: the
file often *starts* with ``last-prompt``/``mode`` records and *ends* with
``cost-state``/``last-prompt``, so the assistant message is never the last
line, and that is the case the scanner has to get right.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

HOME = "/home/tester"
CWD = f"{HOME}/src/demo"
SID = "11111111-2222-4333-8444-555555555555"
OTHER_SID = "99999999-8888-4777-8666-555555555555"

Record = dict[str, Any]


def _base(kind: str, ts: str, cwd: str, entrypoint: str) -> Record:
    """Fields every conversational record carries."""
    return {
        "parentUuid": None,
        "isSidechain": False,
        "type": kind,
        "timestamp": ts,
        "userType": "external",
        "entrypoint": entrypoint,
        "cwd": cwd,
        "sessionId": SID,
    }


def user(
    text: str | list[Record],
    ts: str = "2026-10-22T08:00:00.000Z",
    *,
    cwd: str = CWD,
    entrypoint: str = "cli",
    **extra: object,
) -> Record:
    """A user record; ``text`` may be a string or a list of content blocks."""
    record = _base("user", ts, cwd, entrypoint)
    record["message"] = {"role": "user", "content": text}
    return record | extra


def tool_result(ts: str = "2026-10-22T08:00:01.000Z") -> Record:
    """A user record carrying only a tool result: not a prompt."""
    block = {"type": "tool_result", "tool_use_id": "t1", "content": "ok"}
    return user([block], ts)


def assistant(
    text: str | None,
    ts: str = "2026-10-22T08:00:02.000Z",
    *,
    sidechain: bool = False,
    cwd: str = CWD,
) -> Record:
    """An assistant record; ``None`` means a thinking/tool_use-only record."""
    record = _base("assistant", ts, cwd, "cli")
    record["isSidechain"] = sidechain
    blocks: list[Record] = [{"type": "thinking", "thinking": "", "signature": "x"}]
    if text is None:
        blocks.append({"type": "tool_use", "id": "t1", "name": "Bash", "input": {}})
    else:
        blocks.append({"type": "text", "text": text})
    record["message"] = {"role": "assistant", "type": "message", "content": blocks}
    return record


def ai_title(title: str) -> Record:
    """The record /resume shows as the title."""
    return {"type": "ai-title", "aiTitle": title, "sessionId": SID}


def custom_title(title: str) -> Record:
    """A title the user set with /rename: wins over the generated one."""
    return {"type": "custom-title", "customTitle": title, "sessionId": SID}


def trailer() -> list[Record]:
    """What a real transcript ends with after the last assistant message."""
    return [
        {"type": "cost-state", "sessionId": SID, "totalCostUSD": 0.1},
        {"type": "last-prompt", "lastPrompt": "x", "sessionId": SID},
    ]


def write(
    projects: Path,
    records: list[Record],
    sid: str = SID,
    project_dir: str = "-home-tester-src-demo",
) -> Path:
    """Write one transcript under ``projects`` and return its path."""
    folder = projects / project_dir
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{sid}.jsonl"
    lines = [json.dumps(r, separators=(",", ":")) for r in records]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def projects_dir(sysroot: Path) -> Path:
    """Where the scanner looks under the test root."""
    return sysroot / HOME.lstrip("/") / ".claude/projects"


def session(answer: str, prompt: str = "fix the thing") -> list[Record]:
    """A minimal finished exchange: prompt, tool loop, tagged answer, trailer."""
    return [
        {"type": "mode", "mode": "normal", "sessionId": SID},
        user(prompt, "2026-10-22T08:00:00.000Z"),
        assistant(None, "2026-10-22T08:00:01.000Z"),
        tool_result("2026-10-22T08:00:01.500Z"),
        assistant(answer, "2026-10-22T08:00:02.000Z"),
        *trailer(),
    ]
