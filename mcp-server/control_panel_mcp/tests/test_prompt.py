"""The optimisation prompt must equal the UI's byte for byte.

GOLDEN was produced by running ``web/src/lib/context-prompt.ts`` itself under
node on ROWS (``optimisationPrompt(overLimit(rows), measure)``); regenerate it
the same way whenever that file changes.
"""

from __future__ import annotations

from control_panel_mcp import _prompt

BREACHES = [
    {"hard": True, "limit": 200, "measure": "lines", "why": "only 200 lines load"},
    {"hard": False, "limit": 1250, "measure": "bytes", "why": "cap"},
]
ROWS = [
    {
        "path": "/home/kuhy/.claude/CLAUDE.md",
        "bytes": 4000,
        "lines": 300,
        "tokens": 1000,
        "usd_per_day": 0.25,
        "status": "over hard limit",
        "breaches": BREACHES,
        "budgets": ["250 lines"],
        "hard_limits": ["200 lines"],
    },
    {
        "path": "/srv/b/CLAUDE.md",
        "bytes": None,
        "lines": None,
        "tokens": 0,
        "usd_per_day": 0,
        "status": "over budget",
        "breaches": [],
        "budgets": ["1 KiB"],
        "hard_limits": ["2 KiB"],
    },
    {"path": "/srv/c.md", "bytes": 10, "lines": 1, "tokens": 2.0, "status": "ok"},
]
MEASURE = "wc -lc {paths} {paths}"
GOLDEN_LINES = (
    "Shrink these 2 Claude Code context files below their limits.",
    "",
    "| path | bytes | lines | tokens | limit | standing $/day |",
    "|---|---|---|---|---|---|",
    "| /home/kuhy/.claude/CLAUDE.md | 4000 | 300 | 1000 | 200 lines (hard: only"
    " 200 lines load); 1,250 bytes (budget: cap) | $0.2500 |",
    "| /srv/b/CLAUDE.md | gone | — | 0 | 2 KiB; 1 KiB | $0.0000 |",
    "",
    "For each file: shrink it below its limit without dropping any rule's"
    " prohibition, command, path or memory entry. Move detail to on-demand files"
    " (read only when needed) and link them, rather than deleting it.",
    "Verify every file afterwards with: wc -lc /home/kuhy/.claude/CLAUDE.md"
    " /srv/b/CLAUDE.md {paths}",
    "Commit narrowly: only these files and the on-demand files you create.",
    "",
)
GOLDEN = "\n".join(GOLDEN_LINES)


def test_matches_the_ui_golden() -> None:
    payload = {"files": ROWS, "measure_command": MEASURE}
    assert _prompt.for_payload(payload, []) == GOLDEN


def test_selected_paths_and_no_limit_row() -> None:
    out = _prompt.for_payload({"files": ROWS, "measure_command": MEASURE}, ["c.md"])
    assert "| /srv/c.md | 10 | 1 | 2 | — | $0.0000 |" in out
    assert out.startswith("Shrink these 1 Claude")


def test_legacy_payload_falls_back() -> None:
    rows = [{"path": "/a", "tokens": 3, "warning": "over 40k"}, {"path": "/b"}]
    out = _prompt.for_payload({"files": rows}, [])
    assert "| /a | gone | — | 3 | — | $0.0000 |" in out
    assert out.count("| /") == 1
    assert "Verify every file afterwards with: wc -lc /a  # tokens" in out


def test_nothing_to_do() -> None:
    assert _prompt.for_payload({"files": ROWS[2:]}, []) == (
        "no context file is over a limit"
    )
    assert _prompt.for_payload({}, ["zz"]) == "no listed context file matches ['zz']"


def test_locale_and_js_numbers() -> None:
    assert _prompt._locale(1234.5) == "1,234.5"
    assert _prompt._locale("x") == "x"
    assert _prompt._js(2.5) == "2.5"
