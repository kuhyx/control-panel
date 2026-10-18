"""The context panel's "Copy optimisation prompt", ported line for line.

Source of truth: ``web/src/lib/context-prompt.ts`` (``optimisationPrompt`` and
``overLimit``). Keep the two in step: the point of this tool is that an agent
gets exactly the text the button copies. The fallbacks only cover a dashboard
still serving the older context payload (no ``status`` / ``measure_command``).
"""

from __future__ import annotations

from typing import Any

Row = dict[str, Any]
# context_limits.json's value at the time of porting; used only when the
# payload predates the field.
FALLBACK_MEASURE = (
    "wc -lc {paths}  # tokens ~= bytes / 4; or open /tokens -> Context files"
)


def _js(value: object) -> str:
    """``String(n)`` / ``toLocaleString('en-US')``-free rendering of a number."""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _locale(value: object) -> str:
    """``n.toLocaleString('en-US')`` for the integers the limits use."""
    if isinstance(value, int | float):
        return f"{value:,.3f}".rstrip("0").rstrip(".")
    return str(value)


def status(row: Row) -> str:
    """The row's limit status (older payloads only carry ``warning``)."""
    found = row.get("status")
    if isinstance(found, str):
        return found
    return "over hard limit" if row.get("warning") else "ok"


def over_limit(rows: list[Row]) -> list[Row]:
    """The button's default choice: every file over a hard limit or budget."""
    return [row for row in rows if status(row) != "ok"]


def _limit_text(row: Row) -> str:
    """The breached limits, else every limit, else an em dash."""
    breaches = row.get("breaches") or []
    if not breaches:
        listed = [*(row.get("hard_limits") or []), *(row.get("budgets") or [])]
        return "; ".join(listed) or "—"
    return "; ".join(
        f"{_locale(b.get('limit'))} {b.get('measure')}"
        f" ({'hard' if b.get('hard') else 'budget'}: {b.get('why')})"
        for b in breaches
    )


def optimisation_prompt(rows: list[Row], measure_command: str) -> str:
    """The ready-to-paste prompt for ``rows``."""
    table = []
    for row in rows:
        cells = [
            str(row.get("path")),
            "gone" if row.get("bytes") is None else _js(row["bytes"]),
            "—" if row.get("lines") is None else _js(row["lines"]),
            _js(row.get("tokens")),
            _limit_text(row),
            f"${float(row.get('usd_per_day') or 0):.4f}",
        ]
        table.append(f"| {' | '.join(cells)} |")
    paths = " ".join(str(row.get("path")) for row in rows)
    return "\n".join(
        [
            f"Shrink these {len(rows)} Claude Code context files below their limits.",
            "",
            "| path | bytes | lines | tokens | limit | standing $/day |",
            "|---|---|---|---|---|---|",
            *table,
            "",
            "For each file: shrink it below its limit without dropping any rule's"
            " prohibition, command, path or memory entry. Move detail to on-demand"
            " files (read only when needed) and link them, rather than deleting it.",
            "Verify every file afterwards with:"
            f" {measure_command.replace('{paths}', paths, 1)}",
            "Commit narrowly: only these files and the on-demand files you create.",
            "",
        ]
    )


def for_payload(payload: Row, paths: list[str]) -> str:
    """Pick rows like the button (selection, else over limit) and build it."""
    files = payload.get("files", [])
    chosen = (
        [f for f in files if any(str(f.get("path", "")).endswith(p) for p in paths)]
        if paths
        else over_limit(files)
    )
    if not chosen:
        return (
            f"no listed context file matches {paths}"
            if paths
            else "no context file is over a limit"
        )
    measure = payload.get("measure_command") or FALLBACK_MEASURE
    return optimisation_prompt(chosen, measure)
