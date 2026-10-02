#!/usr/bin/env python3
"""i3 tray icon for control-panel: one click to the whole fleet.

Left-click opens the dashboard in the browser. Right-click lists every
subsystem with a coloured dot, each opening its own dashboards. The icon is a
2x2 grid -- a different silhouette from leetcode-guard's speech bubble and
screen-locker's shield, because at 22px shape is what tells them apart -- and
its colour is the fleet's worst state: red, amber, neutral, or grey when the
panel itself does not answer.

**This script decides nothing.** It renders ``GET /api/tray``, which the
server computes and tests at 100% branch coverage. It runs under the system
Python because PyGObject is not in any venv, the same as the
leetcode-guard and screen-locker trays (``Gtk.StatusIcon``: AppIndicator is
menu-only on left-click, and i3bar implements XEmbed natively).

Installed to ``~/.config/i3/scripts`` by ``install.sh``; edit it here.
"""

from __future__ import annotations

from html import escape
import http.client
import importlib
import json
import logging
import threading
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

# PyGObject is a system package, absent from every venv and lint env, and its
# versions must be pinned before gi.repository is touched -- so all of it is
# loaded by name, after the pins, rather than by import statements.
gi = importlib.import_module("gi")
gi.require_version("Gtk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
GdkPixbuf = importlib.import_module("gi.repository.GdkPixbuf")
GLib = importlib.import_module("gi.repository.GLib")
Gtk = importlib.import_module("gi.repository.Gtk")

HOST = "127.0.0.1"
PORT = 8760
TRAY_PATH = "/api/tray"
PANEL_URL = f"http://{HOST}:{PORT}/"

REFRESH_INTERVAL_S = 30
FETCH_TIMEOUT_S = 15
UNREACHABLE = "unreachable"

# Dracula, the palette i3bar is already drawn in, so the icon reads as part of
# the bar. "ok" is the bar's own foreground: a healthy fleet should be quiet.
COLOURS = {
    "red": "#FF5555",
    "amber": "#FFB86C",
    "ok": "#F8F8F2",
    UNREACHABLE: "#6272A4",
}

# Menu dots differ from the icon in one place: healthy is green, not the bar's
# foreground. In a list of 29 the eye scans for colour, and an off-white dot
# next to off-white text reads as no dot at all.
DOT_COLOURS = {**COLOURS, "ok": "#50FA7B"}

_logger = logging.getLogger("control-panel-tray")


def icon_svg(level: str) -> bytes:
    """A 2x2 grid of rounded squares in the level's colour."""
    colour = COLOURS.get(level, COLOURS[UNREACHABLE])
    cells = "".join(
        f'<rect x="{x}" y="{y}" width="10" height="10" rx="2" fill="{colour}"/>'
        for x in (1, 13)
        for y in (1, 13)
    )
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" '
        f'viewBox="0 0 24 24">{cells}</svg>'
    ).encode()


def render(level: str, size: int) -> object:
    """Rasterise the icon at the size the tray asks for."""
    loader = GdkPixbuf.PixbufLoader.new_with_type("svg")
    loader.set_size(size, size)
    loader.write(icon_svg(level))
    loader.close()
    return loader.get_pixbuf()


def open_url(url: str) -> None:
    """Open a URL in the default browser through GIO, not a child process."""
    try:
        Gtk.show_uri_on_window(None, url, Gtk.get_current_event_time())
    except GLib.Error as exc:
        _logger.warning("could not open %s: %s", url, exc)


def fetch() -> dict[str, Any] | None:
    """GET the tray view, or None when the panel does not answer."""
    conn = http.client.HTTPConnection(HOST, PORT, timeout=FETCH_TIMEOUT_S)
    try:
        conn.request("GET", TRAY_PATH)
        response = conn.getresponse()
        if response.status != http.client.OK:
            _logger.warning("control-panel answered %s", response.status)
            return None
        return json.loads(response.read())
    except (OSError, http.client.HTTPException, json.JSONDecodeError) as exc:
        _logger.warning("control-panel unreachable: %s", exc)
        return None
    finally:
        conn.close()


class Tray:
    """The status icon and the last view it rendered."""

    def __init__(self) -> None:
        """Create the icon; the first refresh fills it in."""
        self.view: dict[str, Any] | None = None
        self.size = 22
        self.icon = Gtk.StatusIcon()
        self.icon.set_title("control-panel")
        self.icon.set_name("control-panel")
        self.icon.connect("activate", lambda _icon: open_url(self.panel_url()))
        self.icon.connect("popup-menu", self.show_menu)
        self.icon.connect("size-changed", self.on_size)
        self.apply(None)

    def panel_url(self) -> str:
        """The dashboard root, as the server reports it."""
        return str(self.view["panel_url"]) if self.view else PANEL_URL

    def level(self) -> str:
        """The icon's colour key."""
        return str(self.view["level"]) if self.view else UNREACHABLE

    def on_size(self, _icon: object, size: int) -> bool:
        """Re-render crisply when the tray changes the icon size."""
        self.size = max(size, 16)
        self.icon.set_from_pixbuf(render(self.level(), self.size))
        return True

    def apply(self, view: dict[str, Any] | None) -> bool:
        """Show a fetched view (or the unreachable state). Runs on the GTK loop."""
        self.view = view
        self.icon.set_from_pixbuf(render(self.level(), self.size))
        tooltip = view["tooltip"] if view else "control-panel: not reachable on :8760"
        self.icon.set_tooltip_text(f"control-panel\n{tooltip}")
        return False  # one-shot idle callback

    def refresh(self) -> bool:
        """Fetch off the GTK loop, then apply on it. Reschedules itself."""

        def work() -> None:
            view = fetch()
            GLib.idle_add(self.apply, view)

        threading.Thread(target=work, daemon=True).start()
        return True

    def _item(
        self, markup: str, on_click: Callable[[], object] | None = None
    ) -> object:
        """A menu item with a Pango-markup label."""
        item = Gtk.MenuItem()
        label = Gtk.Label(xalign=0)
        label.set_markup(markup)
        item.add(label)
        if on_click is not None:
            item.connect("activate", lambda _w: on_click())
        return item

    def _subsystem(self, entry: dict[str, Any]) -> object:
        """One subsystem: a dot, its title, and a submenu of its dashboards."""
        dot = DOT_COLOURS.get(entry["level"], DOT_COLOURS[UNREACHABLE])
        title = escape(str(entry["title"]))
        item = self._item(f'<span foreground="{dot}">●</span>  {title}')
        sub = Gtk.Menu()
        for dash in entry["dashboards"]:
            url = str(dash["url"])
            sub.append(
                self._item(escape(str(dash["label"])), lambda u=url: open_url(u))
            )
        detail = str(entry["panel_url"])
        sub.append(
            self._item("<i>Details in control-panel</i>", lambda: open_url(detail))
        )
        item.set_submenu(sub)
        return item

    def show_menu(self, _icon: object, button: int, time: int) -> None:
        """Right-click: every subsystem, then refresh and quit."""
        menu = Gtk.Menu()
        menu.append(
            self._item("<b>Open control panel</b>", lambda: open_url(self.panel_url()))
        )
        menu.append(Gtk.SeparatorMenuItem())
        if self.view is None:
            menu.append(self._item("<i>panel not reachable on :8760</i>"))
        else:
            for entry in self.view["items"]:
                menu.append(self._subsystem(entry))
        menu.append(Gtk.SeparatorMenuItem())
        menu.append(self._item("Refresh", self.refresh))
        menu.append(self._item("Quit tray icon", Gtk.main_quit))
        menu.show_all()
        menu.popup(None, None, None, self.icon, button, time)


def main() -> None:
    """Create the icon, refresh now and every 30 s, then enter the GTK loop."""
    logging.basicConfig(level=logging.INFO)
    tray = Tray()
    tray.refresh()
    GLib.timeout_add_seconds(REFRESH_INTERVAL_S, tray.refresh)
    Gtk.main()


if __name__ == "__main__":
    main()
