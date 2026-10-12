"""The collector rebuilds only while someone watches, or when a read finds it stale."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from control_panel import _snapshot
from control_panel.tests.test_snapshot import Counting, Ticking

if TYPE_CHECKING:
    import pytest


class Ticks:
    """A monotonic clock the test moves by hand."""

    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def _cache(ticks: Ticks, build: Counting | None = None) -> _snapshot.SnapshotCache:
    return _snapshot.SnapshotCache(build or Counting(), clock=Ticking(), ticks=ticks)


def test_nothing_built_yet_is_always_due() -> None:
    assert _cache(Ticks()).due()


def test_an_unread_snapshot_is_not_rebuilt() -> None:
    ticks = Ticks()
    cache = _cache(ticks)
    cache.refresh()
    assert not cache.due()


def test_a_watching_read_keeps_ticks_due_for_the_active_window() -> None:
    ticks = Ticks()
    cache = _cache(ticks)
    cache.get()
    assert cache.due()
    ticks.now += _snapshot.ACTIVE_WINDOW_SECONDS + 1
    assert not cache.due()


def test_a_tray_read_does_not_count_as_watching() -> None:
    ticks = Ticks()
    cache = _cache(ticks)
    cache.refresh()
    cache.get(watching=False)
    assert not cache.due()


def test_a_read_of_a_stale_snapshot_wakes_the_collector() -> None:
    ticks = Ticks()
    build = Counting()
    cache = _cache(ticks, build)
    cache.refresh()
    ticks.now += _snapshot.IDLE_MAX_AGE_SECONDS
    assert cache.get(watching=False)["build"] == 1
    assert cache.due()


def test_run_skips_ticks_that_are_not_due(monkeypatch: pytest.MonkeyPatch) -> None:
    build = Counting()
    cache = _cache(Ticks(), build)
    cache.refresh()
    answers = iter([False, False])

    def due() -> bool:
        answer = next(answers, None)
        if answer is None:
            cache.stop()
            return False
        return answer

    monkeypatch.setattr(cache, "due", due)
    cache.run(interval=0)
    assert build.calls == 1


def test_stop_wakes_a_waiting_collector() -> None:
    built: list[int] = []

    def build() -> dict[str, Any]:
        built.append(1)
        return {}

    cache = _snapshot.SnapshotCache(build, ticks=Ticks())
    cache.start(interval=3600)
    thread = cache._thread
    cache.stop()
    assert thread is not None
    assert not thread.is_alive()
