"""A small token store, laid out like testsAndMisc's token_dashboard schema."""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import sqlite3

# Monday 2026-09-28 12:00 UTC (14:00 local): far from any DST edge.
T0 = datetime(2026, 9, 28, 12, tzinfo=UTC).timestamp()
DAY = 86400.0

SCHEMA = """
CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE turns(key TEXT, main_key TEXT, is_sub INT, cwd TEXT, ts REAL,
    day TEXT, model TEXT, usd REAL, context INT, prompt_idx INT, input INT,
    cache_write INT, cache_read INT, output INT);
CREATE TABLE session_summary(key TEXT PRIMARY KEY, cwd TEXT, title TEXT,
    first_ts REAL, last_ts REAL, wall_s REAL, active_s REAL, usd REAL,
    usd_main REAL, usd_sub REAL, calls INT, prompts INT, subagents INT,
    models TEXT, final_tag TEXT);
CREATE TABLE prompt_summary(key TEXT, idx INT, ts REAL, text TEXT,
    usd_own REAL, usd_sub REAL, active_s REAL, wall_s REAL, calls INT);
CREATE TABLE subagent_link(sub_key TEXT PRIMARY KEY, main_key TEXT,
    prompt_idx INT, depth INT, description TEXT, agent_type TEXT, model TEXT,
    usd REAL, calls INT, first_ts REAL, last_ts REAL, wall_s REAL,
    active_s REAL);
CREATE TABLE tool_use(key TEXT, prompt_idx INT, name TEXT, calls INT,
    result_tokens INT, usd REAL, carry_usd REAL);
CREATE TABLE snapshots(name TEXT PRIMARY KEY, generated TEXT, since REAL,
    until REAL, metrics TEXT);
CREATE TABLE levers(source TEXT, date TEXT, lever TEXT, metric TEXT,
    baseline REAL, predicted REAL, actual REAL, lower_is_better INT,
    status TEXT, outcome TEXT, detail TEXT);
CREATE TABLE aggregate_sessions(session_id TEXT PRIMARY KEY, source TEXT,
    day TEXT, started REAL, cwd TEXT, title TEXT, input INT, cache_write INT,
    cache_read INT, output INT, api_turns INT, records INT, usd_est REAL);
CREATE TABLE prompt_activity(day TEXT PRIMARY KEY, prompts INT);
CREATE TABLE context_files(path TEXT PRIMARY KEY, kind TEXT, standing TEXT,
    size_limit INT);
CREATE TABLE context_sizes(path TEXT, ts REAL, bytes INT, source TEXT);
"""

AB = {
    "arms": {"sonnet": {"n": 3}, "opus": {"n": 2}},
    "banner": {"level": "grey", "text": "A/B judgment agents: collecting (n=2)"},
}


def _turn(key: str, ts: float, usd: float, **kw: object) -> tuple[object, ...]:
    """One turns row."""
    return (
        key,
        kw.get("main", key.split("/", maxsplit=1)[0]),
        int("/" in key),
        kw.get("cwd", "/home/tester/src/a"),
        ts,
        kw.get("day", "2026-09-28"),
        kw.get("model", "claude-opus-5-5"),
        usd,
        kw.get("context", 1000),
        kw.get("prompt", 0),
        0,
        0,
        0,
        0,
    )


def build(path: Path) -> Path:
    """Write the fixture store and return its path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    turns = [
        _turn("s1", T0, 2.0),
        _turn("s1", T0 + 3600, 1.0, prompt=1, context=400_000),
        _turn("s1/agent-a", T0 + 60, 3.0, model="claude-sonnet-5-5"),
        _turn("s2", T0 + DAY, 4.0, cwd="/home/tester", day="2026-09-29"),
    ]
    conn.executemany("INSERT INTO turns VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", turns)
    models = json.dumps({"claude-opus-5-5": 3.0, "claude-sonnet-5-5": 3.0})
    conn.executemany(
        "INSERT INTO session_summary VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [
            (
                "s1",
                "/home/tester/src/a",
                "fix a",
                T0,
                T0 + 3600,
                3600,
                900,
                6.0,
                3.0,
                3.0,
                3,
                2,
                1,
                models,
                "DONE",
            ),
            (
                "s2",
                "/home/tester",
                "ask",
                T0 + DAY,
                T0 + DAY,
                0,
                0,
                4.0,
                4.0,
                0.0,
                1,
                1,
                0,
                json.dumps({"claude-opus-5-5": 4.0}),
                None,
            ),
        ],
    )
    conn.executemany(
        "INSERT INTO prompt_summary VALUES (?,?,?,?,?,?,?,?,?)",
        [
            ("s1", 0, T0, "fix a", 2.0, 3.0, 600, 3600, 1),
            ("s1", 1, T0 + 3600, "and b", 1.0, 0.0, 300, 10, 1),
        ],
    )
    conn.execute(
        "INSERT INTO subagent_link VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            "s1/agent-a",
            "s1",
            0,
            1,
            "Find x",
            "Explore",
            "claude-sonnet-5-5",
            3.0,
            1,
            T0 + 60,
            T0 + 120,
            60,
            60,
        ),
    )
    conn.executemany(
        "INSERT INTO tool_use VALUES (?,?,?,?,?,?,?)",
        [("s1", 0, "Bash", 2, 500, 1.5, 0.2), ("s1", 0, "Agent", 1, 20, 0.5, 0.0)],
    )
    conn.executemany(
        "INSERT INTO snapshots VALUES (?,?,?,?,?)",
        [
            (
                "2026-09-20",
                "2026-09-20T10:00:00+00:00",
                T0 - 9 * DAY,
                T0 - 2 * DAY,
                json.dumps({"usd_per_day": 9.0, "subagent_usd_share": 0.2}),
            ),
            (
                "2026-09-30",
                "2026-09-30T10:00:00+00:00",
                T0,
                T0 + DAY,
                json.dumps({"usd_per_day": 10.0, "subagent_usd_share": 0.3}),
            ),
        ],
    )
    conn.executemany(
        "INSERT INTO levers VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        [
            (
                "ledger",
                "2026-09-25",
                "routing",
                "subagent_usd_share",
                0.4,
                0.25,
                0.3,
                1,
                "applied",
                "helped",
                "prediction off",
            ),
            (
                "snapshot 2026-09-30",
                "2026-09-30",
                "Large Bash results",
                "bash_big_result_share",
                0.4,
                None,
                None,
                1,
                "proposed",
                None,
                "x",
            ),
        ],
    )
    conn.execute(
        "INSERT INTO aggregate_sessions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            "old",
            "autopsy",
            "2026-07-01",
            T0 - 90 * DAY,
            "/home/tester",
            "t",
            0,
            0,
            0,
            0,
            10,
            20,
            5.0,
        ),
    )
    conn.execute("INSERT INTO prompt_activity VALUES ('2026-03-11', 4)")
    conn.executemany(
        "INSERT INTO meta VALUES (?,?)",
        [
            ("autopsy_calibration", "0.5"),
            ("refreshed_at", str(T0 + 2 * DAY)),
            ("efficiency", json.dumps({"done": [], "commits": [], "estimate": []})),
            ("ab", json.dumps(AB)),
            ("cache_read_usd_per_mtok", "0.2"),
        ],
    )
    home = path.parents[2]
    files = [
        (str(home / ".claude/CLAUDE.md"), "global CLAUDE.md", "always", 40000),
        (str(home / ".claude/memory/MEMORY.md"), "auto-memory index", "always", 100),
        (str(home / "src/a/CLAUDE.md"), "repo CLAUDE.md", "in repo", 40000),
        (str(home / "gone.md"), "rules", "always", None),
    ]
    conn.executemany("INSERT INTO context_files VALUES (?,?,?,?)", files)
    conn.execute(
        "INSERT INTO context_sizes VALUES (?,?,?,?)",
        (files[0][0], T0 - DAY, 4000, "git"),
    )
    for (name, *_), text in zip(files, ("x" * 4000, "y" * 90, "z" * 400), strict=False):
        Path(name).parent.mkdir(parents=True, exist_ok=True)
        Path(name).write_text(text, encoding="utf-8")
    conn.commit()
    conn.close()
    return path
