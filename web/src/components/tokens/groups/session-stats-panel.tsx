import type { Tables } from "../../../lib/tokens-types.ts";

import { formatCount, formatUsd } from "../../../lib/tokens-api.ts";
import { ColumnChart } from "../column-chart.tsx";
import { type ColumnSpec, DataTable } from "../data-table.tsx";
import { LineChart } from "../line-chart.tsx";
import { countColumn, textColumn, usdColumn } from "./tools-columns.tsx";

export interface HistRow {
  bucket: string;
  sessions: number;
}

interface PositionRow {
  bucket: string;
  calls: number;
  mean_usd: null | number;
}

interface DailyRow {
  day: string;
  max_concurrent: number;
  sessions: number;
}

export interface SessionStatsData {
  _tables?: Tables;
  caption: string;
  cost_hist: HistRow[];
  daily: DailyRow[];
  interrupts_hist: HistRow[];
  position: PositionRow[];
  prompts_hist: HistRow[];
  totals: {
    interrupts: number;
    sessions: number;
    usd: number;
    usd_per_session: null | number;
  };
}

const POSITION_COLUMNS: ColumnSpec<PositionRow>[] = [
  textColumn<PositionRow>("bucket", "call position"),
  countColumn<PositionRow>("calls", "calls"),
  usdColumn<PositionRow>("mean_usd", "mean USD per call"),
];

const DAILY_COLUMNS: ColumnSpec<DailyRow>[] = [
  textColumn<DailyRow>("day", "day"),
  countColumn<DailyRow>("sessions", "sessions started"),
  countColumn<DailyRow>("max_concurrent", "max concurrent (10 min)"),
];

export function Histogram({
  label,
  rows,
}: Readonly<{ label: string; rows: HistRow[] }>): React.JSX.Element {
  return (
    <ColumnChart
      columns={rows.map((r) => ({ x: r.bucket, y: r.sessions }))}
      format={formatCount}
      label={label}
      titled
    />
  );
}

export function SessionStatsPanel({
  data,
}: Readonly<{ data: SessionStatsData }>): React.JSX.Element {
  const { totals } = data;
  return (
    <section className="card" id="session-stats">
      <h2>Session stats</h2>
      <ul aria-label="Session stats summary" className="tiles">
        <li className="tile">
          <span className="tile-count hero">
            {formatUsd(totals.usd_per_session)}
          </span>
          <span className="tile-label">per session (mean)</span>
        </li>
        <li className="tile">
          <span className="tile-count">{formatCount(totals.sessions)}</span>
          <span className="tile-label">sessions, {formatUsd(totals.usd)}</span>
        </li>
        <li className="tile">
          <span className="tile-count">{formatCount(totals.interrupts)}</span>
          <span className="tile-label">interruptions</span>
        </li>
      </ul>
      <p className="caption">{data.caption}</p>
      <Histogram label="Sessions by cost" rows={data.cost_hist} />
      <ColumnChart
        columns={data.position.map((r) => {
          return {
            x: r.bucket,
            y: r.mean_usd ?? 0,
          };
        })}
        format={formatUsd}
        label="Mean USD of the n-th call"
        titled
      />
      <Histogram label="Sessions by prompt count" rows={data.prompts_hist} />
      <Histogram
        label="Sessions by interruptions"
        rows={data.interrupts_hist}
      />
      <LineChart
        format={formatCount}
        label="Sessions per day and peak concurrency"
        series={[
          {
            label: "sessions started",
            points: data.daily.map((d) => ({ x: d.day, y: d.sessions })),
          },
          {
            label: "max concurrent (10 min)",
            points: data.daily.map((d) => ({ x: d.day, y: d.max_concurrent })),
          },
        ]}
        titled
      />
      <DataTable<PositionRow>
        columns={POSITION_COLUMNS}
        id="position"
        meta={data._tables?.position}
        rowKey={(row) => row.bucket}
        rows={data.position}
        title="Cost by call position"
      />
      <DataTable<DailyRow>
        columns={DAILY_COLUMNS}
        id="daily"
        meta={data._tables?.daily}
        rowKey={(row) => row.day}
        rows={data.daily}
        title="Sessions per day"
      />
    </section>
  );
}
