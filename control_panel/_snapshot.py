"""Hold the latest fleet snapshot and refresh it off the request path.

A full collection costs about two seconds (dozens of ``systemctl`` and probe
forks). Building it per request made every GET wait that long, and requests
that overlapped made each other slower still. Instead one background thread
rebuilds every :data:`REFRESH_SECONDS` and requests read whatever is cached.

Builds are serialised by one lock, which is also what makes a mutation's
refresh honest: a refresh requested after a change waits for any build already
running, then builds again -- so it can never hand back a snapshot that was
collected before the change.

The collector only works while someone is looking. Each build makes systemd
load and re-parse dozens of unit files and emit a burst of D-Bus signals; doing
that every 10 s around the clock for three days exhausted the system bus on
2026-10-12 (dbus-broker died, logind dropped off, the next login came up
without ``XDG_RUNTIME_DIR`` and so without audio). So a tick rebuilds only
while reads keep arriving (an open dashboard tab polls every 5 s); otherwise a
read of a snapshot older than :data:`IDLE_MAX_AGE_SECONDS` asks for one rebuild.

Nothing here starts a thread on its own. ``serve()`` calls :meth:`start`;
tests call :meth:`refresh` and inject the clock, so they stay deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import logging
import subprocess
import threading
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)

# What one collection can raise: a fork or read that failed (OSError,
# SubprocessError) or output it could not parse. Anything else is a bug and
# should surface rather than hide behind a stale "updated Xs ago".
BUILD_FAULTS = (OSError, subprocess.SubprocessError, ValueError, KeyError, RuntimeError)

# Five times finer than anything in this fleet moves, and the UI polls at 5 s.
REFRESH_SECONDS = 10.0

# A read this recent means a dashboard tab is open: keep every tick fresh.
ACTIVE_WINDOW_SECONDS = 20.0

# Unwatched (only the tray's 30 s background poll, or nobody), a read of a snapshot this
# old wakes the collector for one rebuild instead of it looping regardless.
IDLE_MAX_AGE_SECONDS = 120.0


def _utc_now() -> datetime:
    """Return the current time, timezone-aware UTC."""
    return datetime.now(UTC)


@dataclass(slots=True)
class _Demand:
    """When the snapshot was last read by a watcher, and last built (ticks)."""

    last_read: float | None = None
    built_at: float | None = None


class SnapshotCache:
    """The most recent fleet payload, rebuilt in the background."""

    def __init__(
        self,
        build: Callable[[], dict[str, Any]],
        clock: Callable[[], datetime] = _utc_now,
        ticks: Callable[[], float] = time.monotonic,
    ) -> None:
        """Store the builder, the ``collected_at`` clock and the demand clock."""
        self._build = build
        self._clock = clock
        self._ticks = ticks
        self._demand = _Demand()
        self._wake = threading.Event()
        self._build_lock = threading.Lock()
        self._payload: dict[str, Any] | None = None
        self._generation = 0
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def generation(self) -> int:
        """How many snapshots have been built so far."""
        return self._generation

    def get(self, *, watching: bool = True) -> dict[str, Any]:
        """Return the cached payload, building the first one if none exists.

        A ``watching`` read (the dashboard page) keeps the collector active.
        The always-on tray passes ``watching=False``: counting its 30 s poll
        kept every other tick busy. Any read of a stale snapshot wakes the
        collector, so the next read is fresh without this one waiting.
        """
        if watching:
            self._demand.last_read = self._ticks()
        payload = self._payload
        if payload is not None:
            if self._is_stale():
                self._wake.set()
            return payload
        with self._build_lock:
            # Another request may have finished the first build while this
            # one waited for the lock; one build is enough for both.
            payload = self._payload
            if payload is None:
                payload = self._build_locked()
            return payload

    def refresh(self) -> dict[str, Any]:
        """Build a new snapshot now, after any build already in progress."""
        with self._build_lock:
            return self._build_locked()

    def refresh_if_warm(self) -> None:
        """Rebuild after a change, unless nothing has been collected yet.

        Cold, there is nothing stale to replace: the next :meth:`get` builds
        from scratch, and necessarily after the change. A failed build is
        logged, not raised -- the change itself already happened, and its
        result is what the caller is waiting to report.
        """
        with self._build_lock:
            if self._payload is None:
                return
            try:
                self._build_locked()
            except BUILD_FAULTS:
                logger.exception("refresh after a mutation failed")

    def _build_locked(self) -> dict[str, Any]:
        """Build, stamp and publish one snapshot. Caller holds the lock."""
        built = self._build() | {"collected_at": self._clock().isoformat()}
        # One reference assignment: a concurrent get() sees the old dict or
        # the new one, never a half-built one.
        self._payload = built
        self._demand.built_at = self._ticks()
        self._generation += 1
        return built

    def _is_stale(self) -> bool:
        """Report whether the snapshot is older than the idle ceiling."""
        built_at = self._demand.built_at
        return built_at is None or self._ticks() - built_at >= IDLE_MAX_AGE_SECONDS

    def due(self) -> bool:
        """Report whether a tick should rebuild: nothing built, or watched."""
        if self._payload is None or self._wake.is_set():
            return True
        last_read = self._demand.last_read
        return (
            last_read is not None and self._ticks() - last_read <= ACTIVE_WINDOW_SECONDS
        )

    def run(self, interval: float = REFRESH_SECONDS) -> None:
        """Tick every ``interval`` seconds until :meth:`stop` is called.

        A tick rebuilds only when :meth:`due`; a stale read cuts the wait
        short. A failed build keeps the last good snapshot and is retried next
        tick, so one transient fault does not freeze the dashboard for good.
        """
        while not self._stop.is_set():
            if self.due():
                self._wake.clear()
                try:
                    self.refresh()
                except BUILD_FAULTS:
                    logger.exception("background fleet collection failed")
            self._wake.wait(interval)

    def start(self, interval: float = REFRESH_SECONDS) -> None:
        """Run :meth:`run` on a daemon thread. The first build starts at once."""
        self._stop.clear()
        self._thread = threading.Thread(
            target=self.run, args=(interval,), name="fleet-collector", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        """Ask the collector to exit and wait briefly for it."""
        self._stop.set()
        self._wake.set()
        if self._thread is not None:
            # A build in flight finishes first; it is bounded by the
            # runner's own timeouts, and the thread is a daemon regardless.
            self._thread.join(timeout=1.0)
            self._thread = None
