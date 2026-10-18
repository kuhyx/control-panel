"""Smoke-test the token-dashboard MCP server over real stdio JSON-RPC.

Spawns the server exactly as Claude Code does, lists the tools with the
approximate token size of each schema (chars / 4), then calls a few tools
against the live dashboard and prints their answers.

    ~/.venvs/control-panel-mcp/bin/python -m control_panel_mcp._smoke
"""

from __future__ import annotations

import asyncio
import json
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

CALLS: list[tuple[str, dict[str, object]]] = [
    ("overview", {"window": "7d"}),
    ("sessions", {"limit": 3}),
    ("context_files", {"over_limit_only": True}),
]


def _text(result: object) -> str:
    """The text blocks of a tool result."""
    blocks = getattr(result, "content", [])
    return "\n".join(getattr(b, "text", "") for b in blocks)


async def run(calls: list[tuple[str, dict[str, object]]]) -> None:
    """List tools with schema sizes, then call each of ``calls``."""
    # The SDK passes only a minimal environment by default; forward ours so
    # CONTROL_PANEL_URL (and the tests' fake server) reach the child.
    server = StdioServerParameters(
        command=sys.executable,
        args=["-m", "control_panel_mcp._mcp"],
        env=dict(os.environ),
    )
    async with stdio_client(server) as streams, ClientSession(*streams) as session:
        await session.initialize()
        tools = (await session.list_tools()).tools
        total = 0
        for tool in tools:
            size = len(json.dumps(tool.model_dump(exclude_none=True))) // 4
            total += size
            sys.stdout.write(f"{tool.name:20} ~{size} tok\n")
        sys.stdout.write(f"{'ALL':20} ~{total} tok\n")
        for name, args in calls:
            result = await session.call_tool(name, args)
            sys.stdout.write(f"\n=== {name}({args})\n{_text(result)}\n")


def main() -> None:
    """List the tools, then make the default CALLS."""
    asyncio.run(run(CALLS))


if __name__ == "__main__":
    main()
