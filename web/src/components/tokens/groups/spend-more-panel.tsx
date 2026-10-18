import type { LineSeries } from "../line-chart.tsx";

import { formatCount, formatUsd } from "../../../lib/tokens-api.ts";
import { ColumnChart } from "../column-chart.tsx";
import { DataTable } from "../data-table.tsx";
import { LineChart } from "../line-chart.tsx";
import {
  BLOCK_COLUMNS,
  BLOCK_DAY_COLUMNS,
  type BlockDayRow,
  type BlockRow,
  type CumulativeRow,
  CWD_COLUMNS,
  type CwdRow,
  HEAT_COLUMNS,
  MODEL_COLUMNS,
  type ModelRow,
  MONTH_COLUMNS,
  type MonthRow,
  RATE_COLUMNS,
  type RateLimitRow,
  type SpendMoreData,
} from "./spend-more-columns.tsx";
import { type HeatCell, Heatmap } from "./spend-more-heatmap.tsx";

export type { SpendMoreData } from "./spend-more-columns.tsx";

const CHART_BARS = 10;

export function monthSeries(rows: CumulativeRow[]): LineSeries[] {
  const months = [...new Set(rows.map((r) => r.month))].toSorted((a, b) =>
    a.localeCompare(b),
  );
  return months.map((month) => {
    return {
      label: month,
      points: rows
        .filter((r) => r.month === month)
        .map((r) => ({ x: String(r.dom).padStart(2, "0"), y: r.cum_usd })),
    };
  });
}

function leaf(path: string): string {
  return path.split("/").findLast((part) => part !== "") ?? "/";
}

function Charts({
  data,
}: Readonly<{ data: SpendMoreData }>): React.JSX.Element {
  return (
    <>
      <LineChart
        format={formatUsd}
        label="Cumulative spend within each month"
        series={monthSeries(data.cumulative)}
        titled
      />
      <ColumnChart
        columns={data.months
          .toReversed()
          .map((m) => ({ x: m.month, y: m.usd }))}
        format={formatUsd}
        label="Spend per month"
        titled
      />
      <ColumnChart
        columns={data.by_model
          .slice(0, CHART_BARS)
          .map((r) => ({ x: r.model, y: r.usd }))}
        format={formatUsd}
        label="Spend by model"
        titled
      />
      <ColumnChart
        columns={data.by_cwd
          .slice(0, CHART_BARS)
          .map((r) => ({ note: r.cwd, x: leaf(r.cwd), y: r.usd }))}
        format={formatUsd}
        label="Spend by repo / cwd"
        titled
      />
      <Heatmap grid={data.grid} />
      <LineChart
        format={formatUsd}
        label="Costliest 5-hour block per day"
        series={[
          {
            label: "costliest block",
            points: data.block_daily.map((d) => {
              return {
                x: d.day,
                y: d.max_block_usd,
              };
            }),
          },
        ]}
        titled
      />
      <LineChart
        format={formatCount}
        label="Rate-limit errors per day"
        series={[
          {
            label: "rate-limit errors",
            points: data.rate_limits.map((d) => ({ x: d.day, y: d.errors })),
          },
        ]}
        titled
      />
    </>
  );
}

export function SpendMorePanel({
  data,
}: Readonly<{ data: SpendMoreData }>): React.JSX.Element {
  const tables = data._tables;
  return (
    <section className="card" id="spend-more">
      <h2>Spend breakdown</h2>
      <ul aria-label="Spend breakdown summary" className="tiles">
        <li className="tile">
          <span className="tile-count hero">{formatUsd(data.totals.usd)}</span>
          <span className="tile-label">spend in range</span>
        </li>
        <li className="tile">
          <span className="tile-count">
            {formatUsd(data.totals.peak_block_usd)}
          </span>
          <span className="tile-label">
            costliest of {formatCount(data.totals.blocks)} 5-hour blocks
          </span>
        </li>
        <li className="tile">
          <span className="tile-count">
            {formatCount(data.totals.rate_limit_errors)}
          </span>
          <span className="tile-label">rate-limit errors</span>
        </li>
      </ul>
      <p className="caption">{data.caption}</p>
      <Charts data={data} />
      <DataTable<MonthRow>
        columns={MONTH_COLUMNS}
        id="months"
        meta={tables?.months}
        rowKey={(row) => row.month}
        rows={data.months}
        title="Per month"
      />
      <DataTable<ModelRow>
        columns={MODEL_COLUMNS}
        id="by_model"
        meta={tables?.by_model}
        rowKey={(row) => row.model}
        rows={data.by_model}
        title="By model"
      />
      <DataTable<CwdRow>
        columns={CWD_COLUMNS}
        id="by_cwd"
        meta={tables?.by_cwd}
        rowKey={(row) => row.cwd}
        rows={data.by_cwd}
        title="By repo / cwd"
      />
      <DataTable<HeatCell>
        columns={HEAT_COLUMNS}
        id="heatmap"
        meta={tables?.heatmap}
        rowKey={(row) => `${String(row.weekday)}|${String(row.hour)}`}
        rows={data.heatmap}
        title="Weekday x hour"
      />
      <DataTable<BlockRow>
        columns={BLOCK_COLUMNS}
        id="blocks"
        meta={tables?.blocks}
        rowKey={(row) => String(row.start)}
        rows={data.blocks}
        title="5-hour blocks"
      />
      <DataTable<BlockDayRow>
        columns={BLOCK_DAY_COLUMNS}
        id="block_daily"
        meta={tables?.block_daily}
        rowKey={(row) => row.day}
        rows={data.block_daily}
        title="5-hour blocks per day"
      />
      <DataTable<RateLimitRow>
        columns={RATE_COLUMNS}
        id="rate_limits"
        meta={tables?.rate_limits}
        rowKey={(row) => row.day}
        rows={data.rate_limits}
        title="Rate-limit errors"
      />
    </section>
  );
}
