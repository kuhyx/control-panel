"""The background snapshot cache, and the routes that read through it."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import threading
from typing import Any

from control_panel import _snapshot

_T0 = datetime(2026, 10, 10, 12, 0, tzinfo=UTC)


class Ticking:
    """A clock that moves one second per reading."""

    def __init__(self) -> None:
        self.now = _T0

    def __call__(self) -> datetime:
        self.now += timedelta(seconds=1)
        return self.now


class Counting:
    """A builder that reports how many times it has run."""

    def __init__(self) -> None:
        self.calls = 0

    def __call__(self) -> dict[str, Any]:
        self.calls += 1
        return {"build": self.calls, "subsystems": []}


def _cache(build: Counting | None = None) -> _snapshot.SnapshotCache:
    return _snapshot.SnapshotCache(build or Counting(), clock=Ticking())


def test_first_read_builds_and_later_reads_are_cached() -> None:
    build = Counting()
    cache = _cache(build)
    assert cache.get()["build"] == 1
    assert cache.get()["build"] == 1
    assert build.calls == 1
    assert cache.generation == 1


def test_collected_at_comes_from_the_injected_clock() -> None:
    cache = _cache()
    assert cache.get()["collected_at"] == "2026-10-10T12:00:01+00:00"
    assert cache.refresh()["collected_at"] == "2026-10-10T12:00:02+00:00"


def test_refresh_rebuilds_and_bumps_the_generation() -> None:
    cache = _cache()
    cache.get()
    assert cache.refresh()["build"] == 2
    assert cache.get()["build"] == 2
    assert cache.generation == 2


def test_refresh_if_warm_does_nothing_when_cold() -> None:
    build = Counting()
    cache = _cache(build)
    cache.refresh_if_warm()
    assert build.calls == 0


def test_refresh_if_warm_rebuilds_when_warm() -> None:
    cache = _cache()
    cache.get()
    cache.refresh_if_warm()
    assert cache.get()["build"] == 2


def test_refresh_if_warm_keeps_the_old_snapshot_when_a_build_fails() -> None:
    calls: list[int] = []

    def flaky() -> dict[str, Any]:
        calls.append(1)
        if len(calls) > 1:
            message = "systemctl hung"
            raise RuntimeError(message)
        return {"build": 1}

    cache = _snapshot.SnapshotCache(flaky, clock=Ticking())
    cache.get()
    cache.refresh_if_warm()
    assert cache.get()["build"] == 1


def test_run_survives_a_failed_build_and_stops_when_asked() -> None:
    cache: _snapshot.SnapshotCache
    calls: list[int] = []

    def build() -> dict[str, Any]:
        calls.append(1)
        if len(calls) == 1:
            message = "transient"
            raise RuntimeError(message)
        cache.stop()
        return {"build": len(calls)}

    cache = _snapshot.SnapshotCache(build, clock=Ticking())
    cache.run(interval=0)
    assert len(calls) == 2
    assert cache.get()["build"] == 2


def test_start_collects_on_a_thread_without_waiting_for_a_tick() -> None:
    built = threading.Event()

    def build() -> dict[str, Any]:
        built.set()
        return {}

    cache = _snapshot.SnapshotCache(build, clock=Ticking())
    cache.start(interval=3600)
    try:
        assert built.wait(timeout=5)
    finally:
        cache.stop()


def test_a_refresh_waits_for_an_in_flight_build_then_builds_again() -> None:
    # The mutation's guarantee: a build that started *before* the change must
    # not count as the refresh *after* it.
    entered, release = threading.Event(), threading.Event()
    events: list[str] = []

    def build() -> dict[str, Any]:
        number = sum(1 for event in events if event.startswith("start")) + 1
        events.append(f"start{number}")
        if number == 2:  # the background build, in flight
            entered.set()
            release.wait(timeout=5)
        events.append(f"end{number}")
        return {"build": number}

    cache = _snapshot.SnapshotCache(build, clock=Ticking())
    cache.get()
    background = threading.Thread(target=cache.refresh)
    background.start()
    assert entered.wait(timeout=5)
    # The mutation asks for its refresh while build 2 is still running.
    mutation = threading.Thread(target=cache.refresh_if_warm)
    mutation.start()
    release.set()
    background.join(timeout=5)
    mutation.join(timeout=5)
    assert events.index("start3") > events.index("end2")
    assert cache.get()["build"] == 3


class Announcing:
    """A lock that signals once a second thread starts waiting for it."""

    def __init__(self, second_waiter: threading.Event) -> None:
        self._lock = threading.Lock()
        self._second_waiter = second_waiter
        self._entries = 0

    def __enter__(self) -> None:
        self._entries += 1
        if self._entries == 2:  # the second caller
            self._second_waiter.set()
        self._lock.acquire()

    def __exit__(self, *_: object) -> None:
        self._lock.release()


def test_concurrent_first_reads_share_one_build() -> None:
    # Two cold reads race: the second waits for the first's build and must
    # reuse it rather than collecting again.
    entered, release, waiting = threading.Event(), threading.Event(), threading.Event()
    calls: list[int] = []

    def build() -> dict[str, Any]:
        calls.append(1)
        entered.set()
        release.wait(timeout=5)
        return {"build": len(calls)}

    cache = _snapshot.SnapshotCache(build, clock=Ticking())
    cache._build_lock = Announcing(waiting)
    results: list[dict[str, Any]] = []
    first = threading.Thread(target=lambda: results.append(cache.get()))
    first.start()
    assert entered.wait(timeout=5)
    second = threading.Thread(target=lambda: results.append(cache.get()))
    second.start()
    assert waiting.wait(timeout=5)
    release.set()
    first.join(timeout=5)
    second.join(timeout=5)
    assert len(calls) == 1
    assert len(results) == 2  # both readers answered
    assert results[0] is results[1]
