"""Hold the latest fleet snapshot and refresh it off the request path.

A full collection costs about two seconds (dozens of ``systemctl`` and probe
forks). Building it per request made every GET wait that long, and requests
that overlapped made each other slower still. Instead one background thread
rebuilds every :data:`REFRESH_SECONDS` and requests read whatever is cached.

Builds are serialised by one lock, which is also what makes a mutation's
refresh honest: a refresh requested after a change waits for any build already
running, then builds again -- so it can never hand back a snapshot that was
collected before the change.

Nothing here starts a thread on its own. ``serve()`` calls :meth:`start`;
tests call :meth:`refresh` and inject the clock, so they stay deterministic.
"""

from __future__ import annotations

from datetime import UTC, datetime
import logging
import threading
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)

# Five times finer than anything in this fleet moves, and the UI polls at 5 s.
REFRESH_SECONDS = 10.0


def _utc_now() -> datetime:
    """Return the current time, timezone-aware UTC."""
    return datetime.now(UTC)


class SnapshotCache:
    """The most recent fleet payload, rebuilt in the background."""

    def __init__(
        self,
        build: Callable[[], dict[str, Any]],
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        """Store the builder and the clock that stamps ``collected_at``."""
        self._build = build
        self._clock = clock
        self._build_lock = threading.Lock()
        self._payload: dict[str, Any] | None = None
        self._generation = 0
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def generation(self) -> int:
        """How many snapshots have been built so far."""
        return self._generation

    def get(self) -> dict[str, Any]:
        """Return the cached payload, building the first one if none exists."""
        payload = self._payload
        if payload is not None:
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
            except Exception:
                logger.exception("refresh after a mutation failed")

    def _build_locked(self) -> dict[str, Any]:
        """Build, stamp and publish one snapshot. Caller holds the lock."""
        built = self._build() | {"collected_at": self._clock().isoformat()}
        # One reference assignment: a concurrent get() sees the old dict or
        # the new one, never a half-built one.
        self._payload = built
        self._generation += 1
        return built

    def run(self, interval: float = REFRESH_SECONDS) -> None:
        """Refresh every ``interval`` seconds until :meth:`stop` is called.

        A failed build keeps the last good snapshot and is retried next tick,
        so one transient fault does not freeze the dashboard for good.
        """
        while not self._stop.is_set():
            try:
                self.refresh()
            except Exception:
                logger.exception("background fleet collection failed")
            self._stop.wait(interval)

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
        if self._thread is not None:
            # A build in flight finishes first; it is bounded by the
            # runner's own timeouts, and the thread is a daemon regardless.
            self._thread.join(timeout=1.0)
            self._thread = None
