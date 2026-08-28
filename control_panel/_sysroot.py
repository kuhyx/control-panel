"""Filesystem seam: every absolute path this package reads goes through here.

``CONTROL_PANEL_ROOT`` is read with ``os.environ[...]`` and has **no default**,
copying ``${SERVICES_ROOT?...}`` from ``linux_configuration/periodic_background/
lib/services_common.sh``. A test that forgets to set it raises ``KeyError``
rather than quietly reading the real ``/etc`` -- which is the failure this
project exists to avoid making possible.

An empty value means the real filesystem, so production sets
``CONTROL_PANEL_ROOT=""`` and tests set it to a ``tmp_path``.
"""

from __future__ import annotations

import os
from pathlib import Path

ROOT_ENV = "CONTROL_PANEL_ROOT"


def sysroot() -> str:
    """Return the configured filesystem root as a raw string.

    Deliberately not a ``Path``: ``Path("")`` normalises to ``Path(".")``, so
    wrapping the empty "real filesystem" value in a Path silently turns every
    absolute lookup into a relative one. That bug reported every ExecStart in
    the fleet as missing.

    Raises:
        KeyError: if ``CONTROL_PANEL_ROOT`` is unset. This is deliberate: an
            unset root means a test harness is about to read the live system.
    """
    return os.environ[ROOT_ENV]


def sysroot_path(absolute: str) -> Path:
    """Resolve an absolute system path underneath the configured root.

    ``sysroot_path("/etc/hosts")`` is ``/etc/hosts`` in production and
    ``<tmp>/etc/hosts`` under a test root.
    """
    root = sysroot()
    if not root:
        return Path(absolute)
    return Path(root) / absolute.lstrip("/")


def user_path(relative: str) -> Path:
    """Resolve a path relative to the invoking user's home, under the root.

    ``$HOME`` is used rather than ``Path.home()`` so that a test root can point
    home somewhere disposable without monkeypatching ``pwd``.
    """
    home = os.environ.get("HOME", "/root")
    return sysroot_path(f"{home.rstrip('/')}/{relative.lstrip('/')}")


def exists(absolute: str) -> bool:
    """Report whether an absolute system path exists under the root.

    Swallows ``OSError`` so a permission-denied parent directory reads as
    "absent" instead of taking down a whole collection run.
    """
    try:
        return sysroot_path(absolute).exists()
    except OSError:
        return False
