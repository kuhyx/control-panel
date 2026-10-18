import type { Tables } from "../../../lib/tokens-types.ts";

import { formatCount, formatShare } from "../../../lib/tokens-api.ts";
import { type ColumnSpec, DataTable } from "../data-table.tsx";
import { LineChart } from "../line-chart.tsx";
import {
  countColumn,
  monoColumn,
  shareColumn,
  textColumn,
  usdColumn,
} from "./tools-columns.tsx";

interface ToolStats {
  calls: number;
  denied: number;
  error_rate: null | number;
  errors: number;
  hook: number;
  rejected: number;
  result_p50: null | number;
  result_p95: null | number;
  time_cap: number;
}

export type ToolRow = ToolStats & { name: string };
export type FamilyRow = ToolStats & { family: string };

export interface LoopRow {
  cost_usd: number;
  key: string;
  name: string;
  repeats: number;
  target: string;
}

interface TimeCapRow {
  count: number;
  day: string;
  kind: string;
}

interface BatchRow {
  batched: number;
  calls: number;
  day: string;
  share: null | number;
}

export interface ToolsPanelData {
  _tables?: Tables;
  batching: BatchRow[];
  caption: string;
  families: FamilyRow[];
  loops: LoopRow[];
  time_cap: TimeCapRow[];
  tools: ToolRow[];
  totals: {
    batched_share: null | number;
    calls: number;
    error_rate: null | number;
    errors: number;
    failed: { denied: number; hook: number; rejected: number };
    time_cap_calls: number;
    time_cap_events: null | {
      denied: number;
      killed: number;
      unmatched: number;
    };
  };
}

function statColumns<T extends ToolStats>(): ColumnSpec<T>[] {
  return [
    countColumn<T>("calls", "calls"),
    countColumn<T>("errors", "errors"),
    shareColumn<T>("error_rate", "error rate"),
    countColumn<T>("result_p50", "result p50", "tokens (estimated)"),
    countColumn<T>("result_p95", "result p95", "tokens (estimated)"),
    countColumn<T>("rejected", "rejected"),
    countColumn<T>("denied", "denied"),
    countColumn<T>("hook", "hook-blocked"),
    countColumn<T>("time_cap", "time-cap"),
  ];
}

export const LOOP_COLUMNS: ColumnSpec<LoopRow>[] = [
  monoColumn<LoopRow>("key", "session"),
  textColumn<LoopRow>("name", "tool"),
  monoColumn<LoopRow>("target", "target"),
  countColumn<LoopRow>("repeats", "repeats"),
  usdColumn<LoopRow>("cost_usd", "cost $"),
];

const TIME_CAP_COLUMNS: ColumnSpec<TimeCapRow>[] = [
  textColumn<TimeCapRow>("day", "day"),
  textColumn<TimeCapRow>("kind", "kind"),
  countColumn<TimeCapRow>("count", "count"),
];

const BATCH_COLUMNS: ColumnSpec<BatchRow>[] = [
  textColumn<BatchRow>("day", "day"),
  countColumn<BatchRow>("calls", "calls"),
  countColumn<BatchRow>("batched", "batched calls"),
  shareColumn<BatchRow>("share", "batched share"),
];

function Tiles({
  totals,
}: Readonly<{ totals: ToolsPanelData["totals"] }>): React.JSX.Element {
  const events = totals.time_cap_events;
  return (
    <ul aria-label="Tools summary" className="tiles">
      <li className="tile">
        <span className="tile-count hero">{formatCount(totals.calls)}</span>
        <span className="tile-label">tool calls</span>
      </li>
      <li className="tile">
        <span className="tile-count">{formatShare(totals.error_rate)}</span>
        <span className="tile-label">error rate</span>
      </li>
      <li className="tile">
        <span className="tile-count">
          {formatCount(
            totals.failed.rejected + totals.failed.denied + totals.failed.hook,
          )}
        </span>
        <span className="tile-label">rejected / denied / hook-blocked</span>
      </li>
      <li className="tile">
        <span className="tile-count">
          {events === null ? "—" : formatCount(events.killed)}
        </span>
        <span className="tile-label">
          time-cap kills (log; {formatCount(totals.time_cap_calls)} calls
          marked)
        </span>
      </li>
      <li className="tile">
        <span className="tile-count">{formatShare(totals.batched_share)}</span>
        <span className="tile-label">calls batched with others</span>
      </li>
    </ul>
  );
}

export function ToolsPanel({
  data,
}: Readonly<{ data: ToolsPanelData }>): React.JSX.Element {
  const tables = data._tables;
  return (
    <section className="card" id="tools">
      <h2>Tools</h2>
      <Tiles totals={data.totals} />
      <p className="caption">{data.caption}</p>
      <LineChart
        format={formatShare}
        label="Share of calls batched per day"
        series={[
          {
            label: "batched share",
            points: data.batching.map((d) => ({ x: d.day, y: d.share })),
          },
        ]}
      />
      <DataTable<ToolRow>
        columns={[textColumn<ToolRow>("name", "tool"), ...statColumns()]}
        id="tools"
        meta={tables?.tools}
        rowKey={(row) => row.name}
        rows={data.tools}
        title="By tool"
      />
      <DataTable<FamilyRow>
        columns={[textColumn<FamilyRow>("family", "family"), ...statColumns()]}
        id="families"
        meta={tables?.families}
        rowKey={(row) => row.family}
        rows={data.families}
        title="By family"
      />
      <DataTable<LoopRow>
        columns={LOOP_COLUMNS}
        id="loops"
        meta={tables?.loops}
        rowKey={(row, index) => `${row.key}|${String(index)}`}
        rows={data.loops}
        title="Repeated identical calls (loops)"
      />
      <DataTable<TimeCapRow>
        columns={TIME_CAP_COLUMNS}
        id="time_cap"
        meta={tables?.time_cap}
        rowKey={(row) => `${row.day}|${row.kind}`}
        rows={data.time_cap}
        title="Time-cap log by day"
      />
      <DataTable<BatchRow>
        columns={BATCH_COLUMNS}
        id="batching"
        meta={tables?.batching}
        rowKey={(row) => row.day}
        rows={data.batching}
        title="Batching per day"
      />
    </section>
  );
}
