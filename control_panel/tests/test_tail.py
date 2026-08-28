from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from control_panel import _tail

if TYPE_CHECKING:
    from pathlib import Path


def test_describe_missing_file() -> None:
    stat = _tail.describe("/var/log/nope.log")
    assert not stat.exists
    assert stat.size is None


def test_describe_reports_size_and_rotation(sysroot: Path) -> None:
    log = sysroot / "var/log/x.log"
    log.parent.mkdir(parents=True)
    log.write_text("hello\n")
    (sysroot / "etc/logrotate.d/x").write_text("/var/log/x.log { daily }")
    stat = _tail.describe("/var/log/x.log")
    assert stat.exists
    assert stat.size == 6
    assert stat.rotated
    assert stat.mtime is not None


def test_unrotated_when_no_config_mentions_it(sysroot: Path) -> None:
    log = sysroot / "var/log/lonely.log"
    log.parent.mkdir(parents=True)
    log.write_text("x")
    assert _tail.describe("/var/log/lonely.log").rotated is False


def test_logrotate_dir_missing_is_not_an_error(sysroot: Path) -> None:
    (sysroot / "etc/logrotate.d").rmdir()
    assert not _tail.has_logrotate_entry("/var/log/x.log")


def test_unreadable_logrotate_entry_is_skipped(sysroot: Path) -> None:
    (sysroot / "etc/logrotate.d/subdir").mkdir()
    assert not _tail.has_logrotate_entry("/var/log/x.log")


def test_home_relative_paths_resolve(sysroot: Path) -> None:
    log = sysroot / "home/tester/app.log"
    log.write_text("line\n")
    assert _tail.describe("~/app.log").size == 5


def test_tail_returns_last_lines(sysroot: Path) -> None:
    log = sysroot / "var/log/y.log"
    log.parent.mkdir(parents=True)
    log.write_text("".join(f"line {i}\n" for i in range(50)))
    result = _tail.tail("/var/log/y.log", 3)
    assert result.lines == ("line 47", "line 48", "line 49")
    assert result.truncated


def test_short_file_is_not_truncated(sysroot: Path) -> None:
    log = sysroot / "var/log/z.log"
    log.parent.mkdir(parents=True)
    log.write_text("one\ntwo\n")
    result = _tail.tail("/var/log/z.log", 10)
    assert result.lines == ("one", "two")
    assert not result.truncated


def test_huge_file_reads_only_the_window_and_drops_the_partial_line(
    sysroot: Path,
) -> None:
    log = sysroot / "var/log/big.log"
    log.parent.mkdir(parents=True)
    # Bigger than TAIL_WINDOW, so the seek lands mid-line.
    body = "".join(f"{i:07d} padding padding padding\n" for i in range(4000))
    log.write_text(body)
    assert log.stat().st_size > _tail.TAIL_WINDOW
    result = _tail.tail("/var/log/big.log", 5)
    assert result.truncated
    assert result.total_bytes == log.stat().st_size
    # Every returned line is whole: no half-rendered log entry. Each written
    # line is exactly 31 characters, so a surviving fragment would be shorter.
    assert {len(line) for line in result.lines} == {31}


def test_tail_of_a_missing_file_reports_the_error() -> None:
    result = _tail.tail("/var/log/absent.log")
    assert result.lines == ()
    assert result.error is not None


@pytest.mark.parametrize(("asked", "expected"), [(0, 1), (-5, 1), (99999, 2000)])
def test_line_count_is_clamped(sysroot: Path, asked: int, expected: int) -> None:
    log = sysroot / "var/log/c.log"
    log.parent.mkdir(parents=True)
    log.write_text("".join(f"{i}\n" for i in range(3000)))
    assert len(_tail.tail("/var/log/c.log", asked).lines) == min(expected, 3000)


def test_the_first_non_matching_logrotate_config_is_skipped(sysroot: Path) -> None:
    (sysroot / "etc/logrotate.d/aaa").write_text("/var/log/other.log { daily }")
    (sysroot / "etc/logrotate.d/zzz").write_text("/var/log/wanted.log { daily }")
    assert _tail.has_logrotate_entry("/var/log/wanted.log")
