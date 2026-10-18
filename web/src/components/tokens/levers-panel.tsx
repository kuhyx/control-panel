import type { LeversPanel as Data, LeverRow } from "../../lib/tokens-types.ts";

import { CsvButton } from "./csv.tsx";
import { LineChart, type ReferenceLine } from "./line-chart.tsx";

const formatShare = (n: number): string => `${(n * 100).toFixed(1)}%`;
const formatUsd = (n: number): string => `$${n.toFixed(n < 1 ? 3 : 1)}`;
const formatCount = (n: number): string => (n >= 1000 ? `${(n / 1000).toFixed(1)}K` : n.toFixed(2));

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
  if (lever.baseline !== null) references.push({ label: "baseline", y: lever.baseline });
  if (lever.predicted !== null) references.push({ label: "predicted", y: lever.predicted });
  const daily = series?.daily ?? [];
  return (
    <div>
      <h3>
        {lever.lever} <span className="category">({lever.metric})</span>
      </h3>
      <LineChart
        format={formatMetric(lever.metric)}
        label={`${lever.metric} around ${lever.lever}`}
        markers={lever.date === null ? [] : [{ label: "applied", x: lever.date }]}
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
            points: (series?.snapshots ?? []).map((p) => ({ x: p.date, y: p.value })),
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

const COLUMNS: (keyof LeverRow)[] = [
  "status",
  "outcome",
  "date",
  "lever",
  "metric",
  "baseline",
  "predicted",
  "actual",
  "source",
  "detail",
];

export function LeversPanel({ data }: Readonly<{ data: Data }>): React.JSX.Element {
  const applied = data.rows.filter((r) => r.source === "ledger");
  return (
    <section className="card" id="levers">
      <h2>
        Levers <CsvButton columns={COLUMNS} name="levers.csv" rows={data.rows} />
      </h2>
      <div className="chart-grid-2">
        {applied.map((lever) => {
          return (
            <LeverChart data={data} key={`${lever.lever}${String(lever.date)}`} lever={lever} />
          );
        })}
      </div>
      <h3>Every lever ({data.rows.length})</h3>
      <div className="table-scroll">
        <table className="table tokens-table">
          <thead>
            <tr>
              <th>status</th>
              <th>outcome</th>
              <th>date</th>
              <th>lever</th>
              <th>metric</th>
              <th className="num">baseline</th>
              <th className="num">predicted</th>
              <th className="num">now</th>
              <th>source</th>
            </tr>
          </thead>
          <tbody>
            {data.rows.map((r, index) => {
              return (
                <tr key={`${r.source}${String(index)}`}>
                  <td>{r.status}</td>
                  <td>{r.outcome ?? "—"}</td>
                  <td>{r.date ?? "—"}</td>
                  <td title={r.detail ?? ""}>{r.lever}</td>
                  <td className="mono">{r.metric}</td>
                  <td className="num">{cell(r.baseline)}</td>
                  <td className="num">{cell(r.predicted)}</td>
                  <td className="num">{cell(r.actual)}</td>
                  <td>{r.source}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
