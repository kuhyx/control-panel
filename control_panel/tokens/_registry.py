"""Panel registration: one module per panel group, each self-registering.

Adding a panel is two steps and touches nothing else on the backend:

1. Write ``control_panel/tokens/_<group>.py`` with a function decorated
   ``@panel("<name>", "<title>", order=<n>)`` taking ``(conn, filters)`` and
   returning a JSON-ready dict. Use the shared filters in :mod:`_db`
   (the turns filter clause + ``Filters.params()``) so every panel honours the date
   range, cwd, model and main/subagent scope.
2. Import the module in :mod:`_api` (the import is what registers it).

``GET /api/tokens`` lists the registered panels in ``order``; the frontend
renders the ones it has a component for.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import sqlite3
from typing import Any

from control_panel.tokens._db import Filters

PanelFn = Callable[[sqlite3.Connection, Filters], dict[str, Any]]


@dataclass(frozen=True)
class Panel:
    """A registered panel."""

    name: str
    title: str
    order: int
    build: PanelFn


PANELS: dict[str, Panel] = {}


def panel(name: str, title: str, order: int) -> Callable[[PanelFn], PanelFn]:
    """Register ``fn`` as panel ``name``."""

    def register(fn: PanelFn) -> PanelFn:
        PANELS[name] = Panel(name, title, order, fn)
        return fn

    return register


def listing() -> list[dict[str, Any]]:
    """Registered panels, in display order."""
    return [
        {"name": p.name, "title": p.title}
        for p in sorted(PANELS.values(), key=lambda p: p.order)
    ]
