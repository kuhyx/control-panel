import type { Tables } from "../../../lib/tokens-types.ts";

import {
  formatCount,
  formatDay,
  formatShare,
  formatUsd,
} from "../../../lib/tokens-api.ts";
import { ColumnChart } from "../column-chart.tsx";
import { type ColumnSpec, DataTable } from "../data-table.tsx";

// One estimated session against its real calls (see _estimator.py).
export interface EstimateRow {
  actual_calls: number;
  cwd: string;
  est_calls: number;
  first_ts: number;
  miss: "" | "over" | "under";
  ratio: null | number;
  session_id: string;
  title: string;
  usd: number;
}

// Context-gate misses of one kind on one day.
export interface GateMissRow {
  count: number;
  day: string;
  example: string;
  kind: string;
}

export interface EstimatorPanelData {
  _tables?: Tables;
  caption: string;
  events: GateMissRow[];
  events_daily: { count: number; day: string }[];
  filtered_by: string;
  sessions: EstimateRow[];
  totals: {
    gate_misses: number;
    median_ratio: null | number;
    over_share: null | number;
    predicted_fits: number;
    sessions: number;
    under_share: null | number;
    within_share: null | number;
  };
}

function formatRatio(value: null | number): string {
  return value === null ? "—" : `${value.toFixed(2)}×`;
}

const SESSION_COLUMNS: ColumnSpec<EstimateRow>[] = [
  {
    format: (r) => {
      return (
        <a href={`#/tokens/s/${encodeURIComponent(r.session_id)}`}>
          {r.title === "" ? r.session_id : r.title}
        </a>
      );
    },
    key: "title",
    label: "session",
  },
  {
    format: (r) => <span className="mono">{r.cwd}</span>,
    key: "cwd",
    label: "cwd",
  },
  { format: (r) => formatDay(r.first_ts), key: "first_ts", label: "started" },
  {
    format: (r) => formatCount(r.est_calls),
    key: "est_calls",
    label: "estimated",
    num: true,
    unit: "API calls",
  },
  {
    format: (r) => formatCount(r.actual_calls),
    key: "actual_calls",
    label: "actual",
    num: true,
    unit: "API calls",
  },
  {
    format: (r) => <strong>{formatRatio(r.ratio)}</strong>,
    key: "ratio",
    label: "actual / est",
    num: true,
    unit: "ratio",
  },
  {
    format: (r) => (r.miss === "" ? "within 2×" : r.miss),
    key: "miss",
    label: "miss",
  },
  {
    format: (r) => formatUsd(r.usd),
    key: "usd",
    label: "USD",
    num: true,
    unit: "USD",
  },
];

const EVENT_COLUMNS: ColumnSpec<GateMissRow>[] = [
  { key: "day", label: "day" },
  { key: "kind", label: "why the estimator missed" },
  { key: "count", label: "sessions", num: true },
  { key: "example", label: "latest first prompt" },
];

function Tile({
  hero = false,
  label,
  value,
}: Readonly<{ hero?: boolean; label: string; value: string }>) {
  return (
    <li className="tile">
      <span className={hero ? "tile-count hero" : "tile-count"}>{value}</span>
      <span className="tile-label">{label}</span>
    </li>
  );
}

export function EstimatorPanel({
  data,
}: Readonly<{ data: EstimatorPanelData }>): React.JSX.Element {
  const { totals } = data;
  return (
    <section className="card" id="estimator">
      <h2>Task-size estimator (estimate vs actual calls)</h2>
      <ul aria-label="Estimator summary" className="tiles">
        <Tile
          hero
          label={`of ${formatCount(totals.sessions)} sessions within 2×`}
          value={formatShare(totals.within_share)}
        />
        <Tile label="over (> 2×)" value={formatShare(totals.over_share)} />
        <Tile label="under (< 0.5×)" value={formatShare(totals.under_share)} />
        <Tile
          label="median actual / est"
          value={formatRatio(totals.median_ratio)}
        />
        <Tile label="context-gate misses" value={String(totals.gate_misses)} />
        <Tile
          label="predicted fits, then hit the gate"
          value={String(totals.predicted_fits)}
        />
      </ul>
      <p className="caption">{data.caption}</p>
      <p className="caption">Filtered by: {data.filtered_by}</p>
      <ColumnChart
        columns={data.events_daily.map((d) => ({ x: d.day, y: d.count }))}
        format={formatCount}
        label="Context-gate misses per day"
      />
      <DataTable<EstimateRow>
        columns={SESSION_COLUMNS}
        id="sessions"
        meta={data._tables?.sessions}
        rowKey={(row) => row.session_id}
        rows={data.sessions}
        title="Sessions: estimate vs actual"
      />
      <DataTable<GateMissRow>
        columns={EVENT_COLUMNS}
        id="events"
        meta={data._tables?.events}
        rowKey={(row) => `${row.day}|${row.kind}`}
        rows={data.events}
        title="Context-gate misses by day and kind"
      />
    </section>
  );
}
