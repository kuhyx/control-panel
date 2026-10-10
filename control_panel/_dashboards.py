"""``control-panel dashboards``: is every link in the panel actually usable?

The probe in :mod:`control_panel._probe` asks "is something alive?", where
any answer below 500 counts. This asks the stricter question the tray menu
depends on -- will clicking the link open a page -- so it wants 2xx or 3xx,
plus 401, which is a login prompt the browser handles (dufs). Exit code 1 when
any probed dashboard fails, so the check can gate.
"""

from __future__ import annotations

from typing import IO, TYPE_CHECKING

from control_panel import _live, _manifest

if TYPE_CHECKING:
    from control_panel._live_types import DashboardRecord
    from control_panel._runner import CommandRunner

_USABLE_BELOW = 400
_LOGIN_PROMPT = 401


def verdict(record: DashboardRecord) -> str:
    """Classify one dashboard: ok, login, skipped or FAIL."""
    probe = record.probe
    if record.clash:
        # The link opens somebody else's server, whatever the probe says.
        return "FAIL"
    if probe.up is None:
        return "skipped"
    if probe.status == _LOGIN_PROMPT:
        return "login"
    if probe.up and probe.status is not None and probe.status < _USABLE_BELOW:
        return "ok"
    return "FAIL"


def run(runner: CommandRunner, out: IO[str]) -> int:
    """Probe every declared dashboard, print one line each, return 0 or 1."""
    entries = _manifest.load_manifest()
    views = _live.collect(runner, entries)
    failed = 0
    for entry in entries:
        for record in views[entry.id].dashboards:
            result = verdict(record)
            failed += result == "FAIL"
            detail = record.clash or record.probe.status or record.probe.detail or ""
            out.write(
                f"{result:8} {entry.id:24} {record.label:28} {record.url}  {detail}\n"
            )
    out.write(
        f"\n{failed} dashboard(s) failed.\n" if failed else "\nall dashboards usable.\n"
    )
    return 1 if failed else 0
