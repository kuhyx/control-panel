import type { Tables } from "../../../lib/tokens-types.ts";

import { formatCount, formatDay, formatUsd } from "../../../lib/tokens-api.ts";
import { type ColumnSpec, DataTable } from "../data-table.tsx";
import { LineChart } from "../line-chart.tsx";

// One always-loaded surface kind, at the range start and end (see _prefix.py).
export interface SurfaceRow {
  delta_tokens: number;
  files: number;
  start_tokens: number;
  surface: string;
  tokens: number;
  usd_per_day: null | number;
}

// One stored size point (Git history or a prune run).
export interface PruneRow {
  bytes: number;
  delta_bytes: null | number;
  path: string;
  source: string;
  surface: string;
  ts: number;
}

export interface PrefixPanelData {
  _tables?: Tables;
  caption: string;
  filtered_by: string;
  prunes: PruneRow[];
  series: { label: string; points: { day: string; tokens: number }[] }[];
  surfaces: SurfaceRow[];
  totals: {
    audit_tokens: null | number;
    audit_usd_per_day: null | number;
    calls_per_day: number;
    files_tokens: number;
    files_usd_per_day: null | number;
    price_per_mtok: number;
    pruned_bytes: number;
  };
}

// A signed change: "+20", "−500" (a true minus sign), "—" when unknown.
export function formatDelta(value: null | number): string {
  if (value === null) return "—";
  const sign = value > 0 ? "+" : "";
  return `${sign}${formatCount(value)}`.replace("-", "−");
}

const SURFACE_COLUMNS: ColumnSpec<SurfaceRow>[] = [
  { key: "surface", label: "surface" },
  {
    format: (r) => <strong>{formatUsd(r.usd_per_day)}</strong>,
    key: "usd_per_day",
    label: "$/day",
    num: true,
    unit: "USD/day",
  },
  {
    format: (r) => formatCount(r.tokens),
    key: "tokens",
    label: "tokens now",
    num: true,
    unit: "tokens (bytes/4)",
  },
  {
    format: (r) => formatCount(r.start_tokens),
    key: "start_tokens",
    label: "at range start",
    num: true,
    unit: "tokens (bytes/4)",
  },
  {
    format: (r) => formatDelta(r.delta_tokens),
    key: "delta_tokens",
    label: "change",
    num: true,
    unit: "tokens",
  },
  { key: "files", label: "files", num: true },
];

const PRUNE_COLUMNS: ColumnSpec<PruneRow>[] = [
  { format: (r) => formatDay(r.ts), key: "ts", label: "when" },
  {
    format: (r) => <span className="mono">{r.path}</span>,
    key: "path",
    label: "path",
  },
  { key: "surface", label: "surface" },
  { key: "source", label: "source" },
  {
    format: (r) => formatCount(r.bytes),
    key: "bytes",
    label: "bytes",
    num: true,
    unit: "bytes",
  },
  {
    format: (r) => formatDelta(r.delta_bytes),
    key: "delta_bytes",
    label: "change",
    num: true,
    unit: "bytes",
  },
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

export function PrefixPanel({
  data,
}: Readonly<{ data: PrefixPanelData }>): React.JSX.Element {
  const { totals } = data;
  const audit = totals.audit_tokens;
  return (
    <section className="card" id="prefix">
      <h2>Standing prefix (re-read on every API call)</h2>
      <ul aria-label="Prefix summary" className="tiles">
        <Tile
          hero
          label="audit estimate, tokens"
          value={audit === null ? "—" : formatCount(audit)}
        />
        <Tile
          label="audit estimate, per day"
          value={formatUsd(totals.audit_usd_per_day)}
        />
        <Tile
          label="always-loaded files, tokens"
          value={formatCount(totals.files_tokens)}
        />
        <Tile
          label="always-loaded files, per day"
          value={formatUsd(totals.files_usd_per_day)}
        />
        <Tile
          label="API calls/day"
          value={formatCount(Math.round(totals.calls_per_day))}
        />
        <Tile
          label="bytes pruned in range"
          value={formatCount(totals.pruned_bytes)}
        />
      </ul>
      <p className="caption">{data.caption}</p>
      <p className="caption">Filtered by: {data.filtered_by}</p>
      <LineChart
        format={formatCount}
        label="Standing prefix tokens over time"
        series={data.series.map((s) => {
          return {
            dots: true,
            label: s.label,
            points: s.points.map((p) => ({ x: p.day, y: p.tokens })),
          };
        })}
        titled
      />
      <DataTable<SurfaceRow>
        columns={SURFACE_COLUMNS}
        id="surfaces"
        meta={data._tables?.surfaces}
        rowKey={(row) => row.surface}
        rows={data.surfaces}
        title="Always-loaded surfaces"
      />
      <DataTable<PruneRow>
        columns={PRUNE_COLUMNS}
        id="prunes"
        meta={data._tables?.prunes}
        rowKey={(row, index) => `${row.path}|${String(index)}`}
        rows={data.prunes}
        title="Size history: prune runs and git"
      />
    </section>
  );
}
