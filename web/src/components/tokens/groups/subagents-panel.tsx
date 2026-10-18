import type { Tables } from "../../../lib/tokens-types.ts";

import {
  formatCount,
  formatDuration,
  formatUsd,
} from "../../../lib/tokens-api.ts";
import { type ColumnSpec, DataTable } from "../data-table.tsx";
import {
  countColumn,
  monoColumn,
  textColumn,
  usdColumn,
} from "./tools-columns.tsx";

interface Sums {
  active_s: number;
  agents: number;
  calls: number;
  leverage: null | number;
  returned_tokens: number;
  spent_tokens: number;
  usd: number;
  wall_s: number;
}

export type AgentGroupRow = Sums & { label: string };

interface WorktreeRow {
  day: string;
  key: string;
  sub_key: string;
  target: string;
  usd: null | number;
}

interface AbRow {
  arm: string;
  class: string;
  count: number;
  subagent_type: string;
}

export interface SubagentsPanelData {
  _tables?: Tables;
  by_description: AgentGroupRow[];
  by_model: AgentGroupRow[];
  by_type: AgentGroupRow[];
  caption: string;
  routing: { ab: AbRow[]; gap: string; hook_runs: number; rewrites: number };
  totals: Sums & { worktree_agents: number };
  worktree: WorktreeRow[];
}

export function formatLeverage(value: null | number): string {
  return value === null ? "—" : value.toExponential(2);
}

function perReturned(value: null | number): string {
  return value === null || value === 0
    ? "—"
    : formatCount(Math.round(1 / value));
}

const GROUP_COLUMNS: ColumnSpec<AgentGroupRow>[] = [
  textColumn<AgentGroupRow>("label", "group"),
  countColumn<AgentGroupRow>("agents", "agents"),
  usdColumn<AgentGroupRow>("usd", "USD"),
  countColumn<AgentGroupRow>("calls", "calls"),
  {
    format: (r) => formatDuration(r.wall_s),
    key: "wall_s",
    label: "wall",
    num: true,
    unit: "s",
  },
  {
    format: (r) => formatDuration(r.active_s),
    key: "active_s",
    label: "active",
    num: true,
    unit: "s",
  },
  countColumn<AgentGroupRow>("returned_tokens", "returned", "tokens"),
  countColumn<AgentGroupRow>("spent_tokens", "spent", "tokens"),
  {
    format: (r) => formatLeverage(r.leverage),
    key: "leverage",
    label: "leverage",
    num: true,
    unit: "returned / spent tokens",
  },
];

const WORKTREE_COLUMNS: ColumnSpec<WorktreeRow>[] = [
  textColumn<WorktreeRow>("day", "day"),
  monoColumn<WorktreeRow>("key", "parent session"),
  monoColumn<WorktreeRow>("sub_key", "agent"),
  textColumn<WorktreeRow>("target", "type"),
  usdColumn<WorktreeRow>("usd", "agent USD"),
];

const AB_COLUMNS: ColumnSpec<AbRow>[] = [
  textColumn<AbRow>("arm", "arm"),
  textColumn<AbRow>("class", "class"),
  textColumn<AbRow>("subagent_type", "type"),
  countColumn<AbRow>("count", "spawns"),
];

const GROUPS: {
  id: "by_description" | "by_model" | "by_type";
  title: string;
}[] = [
  { id: "by_type", title: "By agent type" },
  { id: "by_model", title: "By model" },
  { id: "by_description", title: "By description" },
];

export function SubagentsPanel({
  data,
}: Readonly<{ data: SubagentsPanelData }>): React.JSX.Element {
  const { routing, totals } = data;
  return (
    <section className="card" id="subagents">
      <h2>Subagents</h2>
      <ul aria-label="Subagent summary" className="tiles">
        <li className="tile">
          <span className="tile-count hero">{formatUsd(totals.usd)}</span>
          <span className="tile-label">
            {formatCount(totals.agents)} agents, {formatCount(totals.calls)}{" "}
            calls
          </span>
        </li>
        <li className="tile">
          <span className="tile-count">{perReturned(totals.leverage)}</span>
          <span className="tile-label">tokens spent per token returned</span>
        </li>
        <li className="tile">
          <span className="tile-count">
            {formatCount(totals.worktree_agents)}
          </span>
          <span className="tile-label">worktree agents</span>
        </li>
        <li className="tile">
          <span className="tile-count">{formatCount(routing.rewrites)}</span>
          <span className="tile-label">
            model rewrites by the routing hook (of{" "}
            {formatCount(routing.hook_runs)} runs)
          </span>
        </li>
      </ul>
      <p className="caption">{data.caption}</p>
      {GROUPS.map((group) => {
        return (
          <DataTable<AgentGroupRow>
            columns={GROUP_COLUMNS}
            id={group.id}
            key={group.id}
            meta={data._tables?.[group.id]}
            rowKey={(row) => row.label}
            rows={data[group.id]}
            title={group.title}
          />
        );
      })}
      <DataTable<WorktreeRow>
        columns={WORKTREE_COLUMNS}
        id="worktree"
        meta={data._tables?.worktree}
        rowKey={(row, index) => `${row.key}|${String(index)}`}
        rows={data.worktree}
        title="Worktree agents"
      />
      {routing.gap === "" ? null : <p className="caption">{routing.gap}</p>}
      <DataTable<AbRow>
        columns={AB_COLUMNS}
        id="routing.ab"
        meta={data._tables?.["routing.ab"]}
        rowKey={(row) => `${row.arm}|${row.class}|${row.subagent_type}`}
        rows={routing.ab}
        title="Routing A/B arms"
      />
    </section>
  );
}
