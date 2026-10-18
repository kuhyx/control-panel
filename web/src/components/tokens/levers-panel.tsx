import type { LeversPanel as Data, LeverRow } from "../../lib/tokens-types.ts";

import { type ColumnSpec, DataTable } from "./data-table.tsx";
import { LineChart, type ReferenceLine } from "./line-chart.tsx";

const formatShare = (n: number): string => `${(n * 100).toFixed(1)}%`;
const formatUsd = (n: number): string => `$${n.toFixed(n < 1 ? 3 : 1)}`;
const formatCount = (n: number): string =>
  n >= 1000 ? `${(n / 1000).toFixed(1)}K` : n.toFixed(2);

function formatMetric(metric: string): (n: number) => string {
  if (metric.includes("share")) return formatShare;
  return metric.startsWith("usd") ? formatUsd : formatCount;
}

function cell(value: null | number): string {
  return value === null ? "—" : String(value);
}

function LeverChart({
  data,
  lever,
}: Readonly<{ data: Data; lever: LeverRow }>): React.JSX.Element {
  const series = data.series[lever.metric];
  const references: ReferenceLine[] = [];
  if (lever.baseline !== null)
    references.push({ label: "baseline", y: lever.baseline });
  if (lever.predicted !== null)
    references.push({ label: "predicted", y: lever.predicted });
  const daily = series?.daily ?? [];
  return (
    <div>
      <h3>
        {lever.lever} <span className="category">({lever.metric})</span>
      </h3>
      <LineChart
        format={formatMetric(lever.metric)}
        label={`${lever.metric} around ${lever.lever}`}
        markers={
          lever.date === null ? [] : [{ label: "applied", x: lever.date }]
        }
        refLines={references}
        series={[
          ...(daily.length > 0
            ? [
                {
                  label: `rolling ${String(data.rolling_days)}-day`,
                  points: daily.map((p) => ({ x: p.date, y: p.value })),
                },
              ]
            : []),
          {
            dots: true,
            label: "snapshot",
            points: (series?.snapshots ?? []).map((p) => {
              return {
                x: p.date,
                y: p.value,
              };
            }),
          },
        ]}
      />
      <p className="caption">
        Outcome vs newest snapshot: <strong>{lever.outcome ?? "—"}</strong>
        {lever.detail === null ? "" : ` · ${lever.detail}`}
      </p>
    </div>
  );
}

const TABLE: ColumnSpec<LeverRow>[] = [
  { key: "status", label: "status" },
  { format: (r) => r.outcome ?? "—", key: "outcome", label: "outcome" },
  { format: (r) => r.date ?? "—", key: "date", label: "date" },
  {
    format: (r) => <span title={r.detail ?? ""}>{r.lever}</span>,
    key: "lever",
    label: "lever",
  },
  {
    format: (r) => <span className="mono">{r.metric}</span>,
    key: "metric",
    label: "metric",
  },
  {
    format: (r) => cell(r.baseline),
    key: "baseline",
    label: "baseline",
    num: true,
  },
  {
    format: (r) => cell(r.predicted),
    key: "predicted",
    label: "predicted",
    num: true,
  },
  { format: (r) => cell(r.actual), key: "actual", label: "now", num: true },
  { key: "source", label: "source" },
  { key: "detail", label: "detail" },
];

export function LeversPanel({
  data,
}: Readonly<{ data: Data }>): React.JSX.Element {
  const applied = data.rows.filter((r) => r.source === "ledger");
  return (
    <section className="card" id="levers">
      <h2>Levers</h2>
      <div className="chart-grid-2">
        {applied.map((lever) => {
          return (
            <LeverChart
              data={data}
              key={`${lever.lever}${String(lever.date)}`}
              lever={lever}
            />
          );
        })}
      </div>
      <DataTable<LeverRow>
        columns={TABLE}
        id="rows"
        meta={data._tables?.rows}
        rowKey={(r, index) => `${r.source}|${r.lever}|${String(index)}`}
        rows={data.rows}
        title={`Every lever (${String(data._tables?.rows?.total ?? data.rows.length)})`}
      />
    </section>
  );
}
