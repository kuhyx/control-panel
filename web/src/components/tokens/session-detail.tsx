import type {
  SessionDetail as Detail,
  PromptRow,
  SubagentRow,
  ToolRow,
} from "../../lib/tokens-types.ts";

import {
  EMPTY_QUERY,
  fetchSession,
  formatCount,
  formatDay,
  formatDuration,
  formatUsd,
  panelSearch,
  type TokenQuery,
} from "../../lib/tokens-api.ts";
import { useAsync } from "../../lib/use-async.ts";
import { DataTable } from "./data-table.tsx";
import {
  PROMPT_COLUMNS,
  SUBAGENT_COLUMNS,
  TOOL_COLUMNS,
} from "./session-columns.tsx";
import { TableScope } from "./table-scope.tsx";

function Prompt({
  prompt,
  tables,
}: Readonly<{
  prompt: PromptRow;
  tables: Detail["_tables"];
}>): React.JSX.Element {
  return (
    <li className="prompt" id={`prompt-${String(prompt.idx)}`}>
      <div className="prompt-head">
        <span className="prompt-cost">{formatUsd(prompt.usd)}</span>
        <span className="prompt-text">{prompt.text}</span>
        <span className="category">
          {formatDay(prompt.ts)} · active {formatDuration(prompt.active_s)} ·
          own {formatUsd(prompt.usd_own)} + agents {formatUsd(prompt.usd_sub)} ·{" "}
          {prompt.calls} calls
        </span>
      </div>
      {prompt.subagents.length > 0 && (
        <DataTable<SubagentRow>
          columns={SUBAGENT_COLUMNS}
          id="prompts.subagents"
          meta={tables?.["prompts.subagents"]}
          rowKey={(a) => a.key}
          rows={prompt.subagents}
          title="Subagents"
        />
      )}
      {prompt.tools.length > 0 && (
        <DataTable<ToolRow>
          columns={TOOL_COLUMNS}
          id="prompts.tools"
          meta={tables?.["prompts.tools"]}
          rowKey={(t) => t.name}
          rows={prompt.tools}
          title="Tools"
        />
      )}
    </li>
  );
}

export function SessionDetail({
  id,
  onQuery,
  query = EMPTY_QUERY,
}: Readonly<{
  id: string;
  onQuery: (next: TokenQuery) => void;
  query?: TokenQuery;
}>): React.JSX.Element {
  const state = useAsync(
    (signal) => fetchSession(id, signal, query),
    `${id}?${panelSearch(query, "session")}`,
  );
  if (state.error !== null)
    return (
      <p className="empty" role="alert">
        {state.error}
      </p>
    );
  const detail = state.value;
  if (detail === null) return <p className="empty">Reading…</p>;
  const { session } = detail;
  const scope = {
    loadAll: async (table: string): Promise<object[]> => {
      const all = {
        ...query,
        tables: { ...query.tables, [`t.session/${table}.limit`]: "0" },
      };
      const found = await fetchSession(id, undefined, all);
      const rows: unknown = (found as unknown as Record<string, unknown>)[
        table
      ];
      return Array.isArray(rows) ? (rows as object[]) : [];
    },
    onQuery,
    panel: "session",
    query,
    title: "Session",
    window: null,
  };
  return (
    <TableScope scope={scope}>
      <section className="card">
        <p>
          <a href="#/tokens">← all sessions</a>
        </p>
        <h2>{session.title === "" ? session.key : session.title}</h2>
        <p className="category">
          {session.cwd} · {formatDay(session.first_ts)} ·{" "}
          <strong>active {formatDuration(session.active_s)}</strong> of{" "}
          {formatDuration(session.wall_s)} wall · {formatUsd(session.usd)} (
          {formatUsd(session.usd_sub)} in {session.subagents} subagents) ·{" "}
          {formatCount(session.calls)} calls · ended{" "}
          {session.final_tag ?? "untagged"}
        </p>
        <p className="category">
          Prompts sorted by cost. A turn&apos;s USD is split evenly across the
          tools it called (&quot;(no tool)&quot; for text-only turns); carry USD
          is what the result cost by being re-read on every later call until a
          compaction.
        </p>
        <DataTable<PromptRow>
          columns={PROMPT_COLUMNS}
          id="prompts"
          meta={detail._tables?.prompts}
          rowKey={(p) => String(p.idx)}
          rows={detail.prompts}
          title="Prompts"
        />
        <ol className="prompts">
          {detail.prompts.map((p) => <Prompt key={p.idx} prompt={p} tables={detail._tables} />)}
        </ol>
        {detail.unattributed.length > 0 && (
          <DataTable<SubagentRow>
            columns={SUBAGENT_COLUMNS}
            id="unattributed"
            meta={detail._tables?.unattributed}
            rowKey={(a) => a.key}
            rows={detail.unattributed}
            title="Unattributed subagents (spawn not found, e.g. outlived /clear)"
          />
        )}
      </section>
    </TableScope>
  );
}
