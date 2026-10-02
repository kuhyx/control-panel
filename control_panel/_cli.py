"""Command-line entry point.

``CONTROL_PANEL_ROOT`` is defaulted to the empty string (the real filesystem)
here and only here. The library refuses to guess -- see
:mod:`control_panel._sysroot` -- so that a test which forgets to set it fails
loudly instead of reading the live ``/etc``.
"""

from __future__ import annotations

import argparse
import os
import sys

from control_panel import (
    _collect,
    _dashboards,
    _doctor,
    _manifest,
    _sysroot,
    _web_server,
)
from control_panel._runner import SubprocessRunner


def _build_parser() -> argparse.ArgumentParser:
    """Construct the argument parser for every subcommand."""
    parser = argparse.ArgumentParser(
        prog="control-panel",
        description="Read-only dashboard for the enforcement fleet.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("doctor", help="print the arming table and exit")
    subparsers.add_parser("dashboards", help="probe every dashboard link and exit")
    serve = subparsers.add_parser("serve", help="serve the dashboard on loopback")
    serve.add_argument("--port", type=int, default=_web_server.DEFAULT_PORT)
    return parser


def _run_doctor() -> int:
    """Print the fleet arming table. Exit 1 when anything is not armed."""
    entries = _manifest.load_manifest()
    runner = SubprocessRunner()
    view = _collect.read_systemd(runner)
    units = _collect.collect_units(runner, entries, view)
    sys.stdout.write(_doctor.render(entries, units, colour=sys.stdout.isatty()) + "\n")
    found = _doctor.problems(units)
    if found:
        sys.stdout.write(f"\n{len(found)} unit(s) need attention.\n")
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    """Parse arguments and dispatch. Returns the process exit code."""
    os.environ.setdefault(_sysroot.ROOT_ENV, "")
    args = _build_parser().parse_args(argv)
    if args.command == "doctor":
        return _run_doctor()
    if args.command == "dashboards":
        return _dashboards.run(SubprocessRunner(), sys.stdout)
    return _web_server.serve(port=args.port)


if __name__ == "__main__":
    raise SystemExit(main())
