import type { OverviewPanel, TokensIndex } from "../../lib/tokens-types.ts";

import {
  formatCount,
  formatDuration,
  formatShare,
  formatUsd,
} from "../../lib/tokens-api.ts";
import { type Column, ColumnChart } from "./column-chart.tsx";
import { LineChart, type LineSeries, type Point } from "./line-chart.tsx";

type ShareKey = "opus_share" | "over_share" | "sub_share";

const SHARES: { key: ShareKey; label: string; metric: string }[] = [
  { key: "opus_share", label: "Opus share of USD", metric: "opus_usd_share" },
  { key: "sub_share", label: "Subagent share of USD", metric: "subagent_usd_share" },
  {
    key: "over_share",
    label: "Over-budget share (context > 300k)",
    metric: "over_budget_usd_share",
  },
];

function snapshotSeries(
  index: TokensIndex,
  metrics: Record<string, Record<string, number>>,
  metric: string,
): LineSeries {
  const points: Point[] = [];
  for (const name of index.coverage.snapshots) {
    const value = metrics[name]?.[metric];
    if (value !== undefined) points.push({ x: name.slice(0, 10), y: value });
  }
  return { dots: true, label: "token_audit snapshot", points };
}

export function SpendPanel({
  data,
  index,
  snapshotMetrics,
}: Readonly<{
  data: OverviewPanel;
  index: TokensIndex;
  snapshotMetrics: Record<string, Record<string, number>>;
}>): React.JSX.Element {
  const { tiles } = data;
  const daily: Column[] = [
    ...data.aggregate.map((row) => {
      return {
        aggregate: true,
        note: `${String(row.sessions)} sessions, estimate, main only`,
        x: row.day,
        y: row.usd_est,
      };
    }),
    ...data.daily.map((row) => ({ x: row.day, y: row.usd })),
  ].toSorted((a, b) => a.x.localeCompare(b.x));
  const line = (key: "usd_per_call", label: string): LineSeries => {
    return {
      label,
      points: data.daily.map((row) => ({ x: row.day, y: row[key] })),
    };
  };
  return (
    <section className="card" id="spend">
      <h2>Spend</h2>
      <ul aria-label="Spend summary" className="tiles">
        <li className="tile">
          <span className="tile-count hero">{formatUsd(tiles.usd_per_day)}</span>
          <span className="tile-label">USD/day (over the record span)</span>
        </li>
        <li className="tile">
          <span className="tile-count">{formatUsd(tiles.usd)}</span>
          <span className="tile-label">USD in range</span>
        </li>
        <li className="tile">
          <span className="tile-count">{formatCount(tiles.calls)}</span>
          <span className="tile-label">API calls</span>
        </li>
        <li className="tile">
          <span className="tile-count">{formatUsd(tiles.usd_per_call)}</span>
          <span className="tile-label">USD per call</span>
        </li>
        <li className="tile">
          <span className="tile-count">{formatDuration(tiles.active_h * 3600)}</span>
          <span className="tile-label">active time, {tiles.sessions} sessions</span>
        </li>
      </ul>
      <h3>USD per day</h3>
      <ColumnChart
        aggregateLabel="aggregate only (autopsy estimate, main sessions)"
        columns={daily}
        format={formatUsd}
        label="USD per day"
      />
      <h3>USD per week</h3>
      <ColumnChart
        columns={data.weekly.map((w) => ({ x: w.week, y: w.usd }))}
        format={formatUsd}
        label="USD per week"
      />
      <div className="chart-grid-2">
        <div>
          <h3>USD per call</h3>
          <LineChart
            format={(n) => `$${n.toFixed(3)}`}
            label="USD per call"
            series={[
              line("usd_per_call", "daily"),
              snapshotSeries(index, snapshotMetrics, "usd_per_call"),
            ]}
          />
        </div>
        <div>
          <h3>Calls per day</h3>
          <ColumnChart
            columns={data.daily.map((row) => ({ x: row.day, y: row.calls }))}
            format={(n) => formatCount(Math.round(n))}
            label="Calls per day"
          />
        </div>
        {SHARES.map((share) => {
          return (
            <div key={share.key}>
              <h3>{share.label}</h3>
              <LineChart
                format={formatShare}
                label={share.label}
                series={[
                  {
                    label: "daily",
                    points: data.daily.map((row) => ({ x: row.day, y: row[share.key] })),
                  },
                  snapshotSeries(index, snapshotMetrics, share.metric),
                ]}
              />
            </div>
          );
        })}
        <div>
          <h3>Prompts per day (aggregate only: ~/.claude/history.jsonl)</h3>
          <ColumnChart
            columns={data.prompts.map((p) => ({ aggregate: true, x: p.day, y: p.prompts }))}
            format={(n) => formatCount(Math.round(n))}
            label="Prompts per day"
          />
        </div>
      </div>
    </section>
  );
}
