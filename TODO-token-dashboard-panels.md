# TODO: remaining /tokens statistics panels

REMOVE ME AFTER FINISH

kuhy asked for "all possible statistics" on `/tokens`. The core spec, the three
efficiency charts, the A/B judgment-agent panel and the context-files inspector
are built. This file lists the catalogue groups still to build. All 0-token:
local parsing only, no LLM.

## How to add a panel (the registration pattern)

1. **Data** (testsAndMisc, `python_pkg/token_dashboard/`): if the raw rows a
   group needs are not stored yet, extend `walk.py` (+ `rows.py`, `store.py`,
   `schema.py`). A new column = bump `schema.VERSION` **and add an
   `ALTER TABLE ... ADD COLUMN` entry to `schema.MIGRATIONS`**; insert with
   named columns. **Never delete `~/data/token-dashboard/tokens.sqlite`**: it
   holds spend of transcripts that no longer exist. To backfill a new raw
   column for files still on disk, `DELETE FROM files` (forces a re-walk;
   rows of vanished files are untouched) and run the ingest in <60 s
   chunks. Precomputed aggregates go in `meta` as JSON (see
   `efficiency.rebuild`, `ab.rebuild`) or their own table. Tests next to it.
2. **Backend** (this repo): add `control_panel/tokens/_<group>.py` with
   `@panel("<name>", "<title>", order=<n>)` on a `build(conn, filters)` that
   returns a JSON-ready dict, and import it in `control_panel/tokens/_api.py`.
   Queries over `turns` must end with the shared filter clause (see the
   comment in `_db.py`) and bind `filters.params()`, so date range, cwd, model
   and main/subagent scope apply. No SQL built from strings, no `noqa`.
   Tests: extend `control_panel/tests/_fixture_tokens.py`; 100% coverage.
3. **Frontend**: `web/src/components/tokens/groups/<group>-panel.tsx`
   (component + its types) and `panels/<group>-view.tsx` exporting `view`
   (self-registered, fetched by LazyPanel; `#/tokens/p/<name>` shows it
   alone). Every table is a `DataTable` (search/filter/sort in the hash,
   Copy for Claude, CSV). Charts: `LineChart` / `ColumnChart` (dataviz:
   cat-2, cat-3, cat-5 in that order; never dual-axis; legend for >= 2
   series). Raw detail rows: `calls`, `marks`, `turn_detail` tables
   (testsAndMisc `detail*.py`, `marks.py`). Every file <= 250 lines.

## Done so far

- Spend (A, partly): USD per day/week, tiles, USD/call, calls/day, Opus /
  subagent / over-budget share, aggregate-only history (autopsy, prompts).
- Sessions (I, partly): ranked list; drill-down by prompt with subagents and
  tools (USD split per tool, carry USD).
- Efficiency (L, partly): USD per DONE session, per surviving commit, per
  estimated size unit.
- Levers (M, partly): ledger, candidates (structured + markdown), prune
  proposals, metric charts with applied markers.
- A/B judgment subagents, banner on every view, `/api/tokens/ab` for the tray.
- Context files inspector (E, partly): per-file live size/tokens/$ per day,
  size history (git + prune sizes), limits, content + git log.
- CSV export (Q) on the session, lever and context tables.

## Remaining groups

- [ ] **A. Spend**: per-month totals and cumulative month; spend by model and
      by repo/cwd as charts; hour-of-day x weekday heatmap; Max-plan 5-hour
      window burn per block; rate-limit / usage-limit errors seen.
- [ ] **B. Token classes**: input / cache write (5m vs 1h from the split) /
      cache read / output over time; cache hit ratio; cache-write waste
      (writes never re-read); cold starts; compaction events and cost.
- [ ] **C. Context**: per-call context size distribution; growth curve per
      session; sessions crossing 250k/300k; handoffs generated.
- [x] **D. Carry-cost attribution** (KEY METRIC; `tool_use.carry_usd` already
      stored per prompt+tool): by Bash command family, MCP server/tool,
      skill load, hook-injected context per hook, memory/rules/CLAUDE.md
      reads, images (count, tokens, carry), top re-read paths,
      WebFetch/WebSearch. Needs per-call rows (command text, path) in walk.
- [ ] **E. Standing prefix**: per-surface totals over time from
      `token_audit.checkup` + prune sizes, $/day; prune history timeline.
- [ ] **F. Hooks**: fires, injected tokens, blocks/denials + cost of the
      retry, runtime (hook budget-gate log under ~/.claude/logs), Stop-hook
      status-tag bounces and their cost.
- [ ] **G. Tools**: error rate, result-token p50/p95, failed/denied,
      time-cap kills (`events` table already has time-cap rows), repeated
      identical commands (loops), batching rate.
- [ ] **H. Subagents**: by type/model/description; leverage ratio (tokens
      returned to parent vs spent); routing-hook decisions; worktree agents.
- [ ] **I. Sessions**: $/session histogram; cost by call position; user-turn
      count; interruptions; concurrent sessions over time; sessions/day.
- [ ] **J. Latency**: per-call model latency, tool execution time, user
      think-time gaps.
- [ ] **K. Output**: thinking / text / tool_use output split; output $ share;
      longest replies.
- [ ] **L. Efficiency**: cost per user prompt.
- [ ] **M. Levers**: task-size estimator verdicts and misses panel
      (`estimates` + `events` tables hold the data).
- [ ] **N. Anomalies**: day-over-day spikes, sessions over $X, runaway loops,
      polling / lint-test / VCS turns (session-autopsy categories).
- [ ] **O. Errors**: API errors (overloaded, 5xx, rate limit), retries, tool
      errors by type.
- [ ] **P. Prompt habits**: prompt length vs session cost; LONG:/OPUS:/HERE:/
      override/SOLVE: prefix counts; sessions started from ~.
- [ ] Filters: efficiency and A/B panels ignore cwd/model/scope (precomputed);
      context calls/day and the sessions list now honour them.

References for panel choice: Grafana Claude Code OTel dashboards 25052 /
25255; Helicone / Langfuse (latency percentiles, cost per feature, week-over-week
token-per-request growth alert).
