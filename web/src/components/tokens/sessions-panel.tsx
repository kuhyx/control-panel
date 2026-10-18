import type {
  SessionsPanel as Data,
  SessionRow,
} from "../../lib/tokens-types.ts";

import {
  formatCount,
  formatDay,
  formatDuration,
  formatUsd,
} from "../../lib/tokens-api.ts";
import { type ColumnSpec, DataTable } from "./data-table.tsx";

export function shortCwd(cwd: null | string): string {
  return cwd === null ? "—" : cwd.replace(/^\/home\/[^/]+/, "~");
}

function topModel(models: Record<string, number>): string {
  const [best] = Object.entries(models).toSorted((a, b) => b[1] - a[1]);
  return best === undefined ? "—" : best[0].replace(/^claude-/, "");
}

const SCOPE_LABEL: Record<string, string> = {
  main: "USD (main)",
  sub: "USD (agents)",
};

function columns(scope: string): ColumnSpec<SessionRow>[] {
  return [
    {
      format: (s) => formatDay(s.first_ts),
      key: "first_ts",
      label: "started",
      unit: "unix s",
    },
    {
      format: (s) => <span className="mono">{shortCwd(s.cwd)}</span>,
      key: "cwd",
      label: "repo / cwd",
    },
    {
      format: (s) => {
        return (
          <a href={`#/tokens/s/${encodeURIComponent(s.key)}`}>
            {s.title === "" ? s.key : s.title}
          </a>
        );
      },
      key: "title",
      label: "first prompt",
    },
    {
      format: (s) => formatDuration(s.active_s),
      key: "active_s",
      label: "active",
      num: true,
      unit: "s",
    },
    {
      format: (s) => formatDuration(s.wall_s),
      key: "wall_s",
      label: "wall",
      num: true,
      unit: "s",
    },
    {
      format: (s) => <strong>{formatUsd(s.usd_scope ?? s.usd)}</strong>,
      key: "usd_scope",
      label: SCOPE_LABEL[scope] ?? "USD",
      num: true,
      unit: "USD",
    },
    {
      format: (s) => formatUsd(s.usd_sub),
      key: "usd_sub",
      label: "of which agents",
      num: true,
      unit: "USD",
    },
    {
      format: (s) => formatCount(s.calls),
      key: "calls",
      label: "calls",
      num: true,
    },
    { key: "prompts", label: "prompts", num: true },
    { format: (s) => topModel(s.models), key: "models", label: "model" },
    { format: (s) => s.final_tag ?? "—", key: "final_tag", label: "end" },
  ];
}

const RANKED: Record<string, string> = {
  main: ", ranked by their main-session spend",
  sub: ", ranked by their subagent spend",
};

export function SessionsPanel({
  data,
}: Readonly<{ data: Data }>): React.JSX.Element {
  const scope = data.scope ?? "all";
  return (
    <section className="card" id="sessions">
      <h2>Sessions by cost</h2>
      <DataTable<SessionRow>
        caption={
          <p className="category">
            Sessions that started in range, top {data.limit} by default
            {RANKED[scope] ?? ""}
            . Active time sums the gaps between consecutive records of the
            session and its subagents, a gap over 5 minutes counting as zero;
            wall time is first to last record.
          </p>
        }
        columns={columns(scope)}
        id="sessions"
        meta={data._tables?.sessions}
        rowKey={(s) => s.key}
        rows={data.sessions}
        title="Sessions"
      />
    </section>
  );
}
