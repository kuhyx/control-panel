"""Panel registration: one module per panel group, each self-registering.

Adding a panel touches no shared file:

1. Write ``control_panel/tokens/_<group>.py`` with a function decorated
   ``@panel("<name>", "<title>", order=<n>, tables={...})`` taking
   ``(conn, filters)`` and returning a JSON-ready dict. Every query ends with
   the shared filter clause (see :mod:`_db`) and binds ``Filters.params()``;
   tables are lists of flat dicts, which :mod:`_tables` searches, filters,
   sorts and limits for every client alike (``tables`` sets defaults).
   :mod:`_api` imports every module of the package, which registers it.
2. Frontend: ``web/src/components/tokens/groups/<group>-panel.tsx`` plus
   ``panels/<group>-view.tsx`` exporting ``view`` (picked up by a glob);
   every table is a ``DataTable``. ``#/tokens/p/<name>`` shows it alone.

``GET /api/tokens`` lists the registered panels in ``order``;
``GET /api/tokens/schema`` describes each one's tables and columns.
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
    # Default table parameters (see _tables), e.g. {"sessions": {"limit": "200"}}.
    tables: dict[str, dict[str, str]] | None = None


PANELS: dict[str, Panel] = {}


def panel(
    name: str,
    title: str,
    order: int,
    tables: dict[str, dict[str, str]] | None = None,
) -> Callable[[PanelFn], PanelFn]:
    """Register ``fn`` as panel ``name`` (``tables``: default table params)."""

    def register(fn: PanelFn) -> PanelFn:
        PANELS[name] = Panel(name, title, order, fn, tables)
        return fn

    return register


def listing() -> list[dict[str, Any]]:
    """Registered panels, in display order."""
    return [
        {"name": p.name, "title": p.title}
        for p in sorted(PANELS.values(), key=lambda p: p.order)
    ]
