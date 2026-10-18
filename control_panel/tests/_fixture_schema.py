"""The fixture store's tables, laid out like token_dashboard's schema."""

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
CREATE TABLE calls(key TEXT, main_key TEXT, is_sub INT, cwd TEXT, model TEXT,
    ts REAL, day TEXT, prompt_idx INT, end_ts REAL, name TEXT, family TEXT,
    target TEXT, sig TEXT, batch INT, result_tokens INT, images INT,
    is_error INT, error_kind TEXT, create_usd REAL, carry_usd REAL,
    carry_calls INT);
CREATE TABLE marks(key TEXT, main_key TEXT, is_sub INT, cwd TEXT, model TEXT,
    ts REAL, day TEXT, prompt_idx INT, kind TEXT, name TEXT, detail TEXT,
    count INT, tokens INT, extra INT, duration_ms INT, retry_usd REAL,
    create_usd REAL, carry_usd REAL, carry_calls INT);
CREATE TABLE turn_detail(key TEXT, main_key TEXT, is_sub INT, cwd TEXT,
    model TEXT, ts REAL, day TEXT, prompt_idx INT, latency_s REAL, cw_1h INT,
    cw_5m INT, out_text INT, out_tool INT, out_think INT, tool_calls INT);
CREATE TABLE prompts(key TEXT, idx INT, ts REAL, prompt_id TEXT, text TEXT);
CREATE TABLE sessions(key TEXT PRIMARY KEY, session_id TEXT, main_key TEXT,
    cwd TEXT, agent_type TEXT, description TEXT, spawn_tool_use_id TEXT,
    parent_agent_id TEXT, agent_model TEXT, first_ts REAL, last_ts REAL,
    final_tag TEXT);
CREATE TABLE agent_calls(key TEXT, tool_use_id TEXT, agent_id TEXT,
    prompt_idx INT, ts REAL, description TEXT, subagent_type TEXT, model TEXT,
    result_ts REAL, status TEXT);
CREATE TABLE events(source TEXT, ts REAL, kind TEXT, detail TEXT);
CREATE TABLE estimates(session_id TEXT PRIMARY KEY, est_calls INT);
CREATE TABLE session_commits(sha TEXT PRIMARY KEY, repo TEXT, ts REAL,
    key TEXT, prompt_idx INT);
CREATE TABLE commit_verdicts(sha TEXT PRIMARY KEY, repo TEXT, ts REAL,
    added INT, kept INT, verdict TEXT);
"""
