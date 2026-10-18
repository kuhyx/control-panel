import type { Tables } from "../../../lib/tokens-types.ts";

import {
  formatCount,
  formatDay,
  formatShare,
} from "../../../lib/tokens-api.ts";
import { type ColumnSpec, DataTable } from "../data-table.tsx";
import { LineChart } from "../line-chart.tsx";
import {
  API_DETAIL_COLUMNS,
  API_TYPE_COLUMNS,
  type ApiErrorRow,
  type ApiErrorTypeRow,
  type ErrorKindRow,
  type ErrorToolRow,
  KIND_COLUMNS,
  RECENT_COLUMNS,
  type RecentErrorRow,
  TOOL_COLUMNS,
} from "./errors-columns.tsx";

interface DailyErrors {
  api_errors: number;
  calls: number;
  day: string;
  error_rate: null | number;
  interrupts: number;
  rate_limits: number;
  tool_errors: number;
}

export interface ErrorsPanelData {
  _tables?: Tables;
  api_error_types: ApiErrorTypeRow[];
  api_errors: ApiErrorRow[];
  caption: string;
  daily: DailyErrors[];
  error_kinds: ErrorKindRow[];
  error_tools: ErrorToolRow[];
  recent: RecentErrorRow[];
  totals: {
    api_errors: number;
    calls: number;
    error_rate: null | number;
    interrupts: number;
    last_rate_limit_ts: null | number;
    rate_limit_hits: number;
    rate_limit_sessions: number;
    tool_errors: number;
  };
}

function Tiles({
  totals,
}: Readonly<{ totals: ErrorsPanelData["totals"] }>): React.JSX.Element {
  const last =
    totals.last_rate_limit_ts === null
      ? "no hits"
      : `in ${String(totals.rate_limit_sessions)} sessions, last ${formatDay(totals.last_rate_limit_ts)}`;
  const tiles: [string, string][] = [
    [last, "rate-limit sessions"],
    [formatCount(totals.api_errors), "API errors (all types)"],
    [formatCount(totals.interrupts), "interrupts"],
    [formatShare(totals.error_rate), "tool error rate"],
    [
      formatCount(totals.tool_errors),
      `failing of ${formatCount(totals.calls)} tool calls`,
    ],
  ];
  return (
    <ul aria-label="Error summary" className="tiles">
      <li className="tile">
        <span className="tile-count hero">
          {formatCount(totals.rate_limit_hits)}
        </span>
        <span className="tile-label">rate-limit / usage-limit hits</span>
      </li>
      {tiles.map(([value, label]) => {
        return (
          <li className="tile" key={label}>
            <span className="tile-count">{value}</span>
            <span className="tile-label">{label}</span>
          </li>
        );
      })}
    </ul>
  );
}

function Table<T extends object>({
  columns,
  data,
  id,
  rows,
  title,
}: Readonly<{
  columns: ColumnSpec<T>[];
  data: ErrorsPanelData;
  id: string;
  rows: T[];
  title: string;
}>): React.JSX.Element {
  return (
    <DataTable<T>
      columns={columns}
      id={id}
      meta={data._tables?.[id]}
      rowKey={(_row, index) => `${id}|${String(index)}`}
      rows={rows}
      title={title}
    />
  );
}

export function ErrorsPanel({
  data,
}: Readonly<{ data: ErrorsPanelData }>): React.JSX.Element {
  const points = (pick: (d: DailyErrors) => null | number) =>
    data.daily.map((d) => ({ x: d.day, y: pick(d) }));
  return (
    <section className="card" id="errors">
      <h2>Errors (API, limits, interrupts, tool calls)</h2>
      <Tiles totals={data.totals} />
      <p className="caption">{data.caption}</p>
      <LineChart
        format={formatCount}
        label="API errors and interrupts per day"
        series={[
          {
            label: "rate / usage limits",
            points: points((d) => d.rate_limits),
          },
          {
            label: "other API errors",
            points: points((d) => d.api_errors - d.rate_limits),
          },
          { label: "interrupts", points: points((d) => d.interrupts) },
        ]}
        titled
      />
      <LineChart
        format={formatShare}
        label="Tool error rate per day"
        series={[
          { label: "failing / all calls", points: points((d) => d.error_rate) },
        ]}
        titled
      />
      <Table
        columns={API_TYPE_COLUMNS}
        data={data}
        id="api_error_types"
        rows={data.api_error_types}
        title="API errors by type"
      />
      <Table
        columns={API_DETAIL_COLUMNS}
        data={data}
        id="api_errors"
        rows={data.api_errors}
        title="API errors by message"
      />
      <Table
        columns={KIND_COLUMNS}
        data={data}
        id="error_kinds"
        rows={data.error_kinds}
        title="Tool errors by kind"
      />
      <Table
        columns={TOOL_COLUMNS}
        data={data}
        id="error_tools"
        rows={data.error_tools}
        title="Tool errors by tool / command family"
      />
      <Table
        columns={RECENT_COLUMNS}
        data={data}
        id="recent"
        rows={data.recent}
        title="Latest failing calls"
      />
    </section>
  );
}
