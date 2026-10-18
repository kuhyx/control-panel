import type { Tables } from "../../../lib/tokens-types.ts";

import { formatCount, formatDuration } from "../../../lib/tokens-api.ts";
import { ColumnChart } from "../column-chart.tsx";
import { type ColumnSpec, DataTable } from "../data-table.tsx";
import { LineChart } from "../line-chart.tsx";

interface Spread {
  calls: number;
  p50: null | number;
  p90: null | number;
  p99: null | number;
  total_s: number;
}

type ModelRow = Spread & { model: string };

interface ToolRow {
  calls: number;
  name: string;
  p50: null | number;
  p95: null | number;
  total_s: number;
}

export interface LatencyData {
  _tables?: Tables;
  caption: string;
  daily: (Spread & { day: string })[];
  models: ModelRow[];
  think: { p50: null | number; p90: null | number; prompts: number };
  think_histogram: { bucket: string; prompts: number }[];
  tools: ToolRow[];
}

// Sub-minute latencies need a decimal; formatDuration rounds to whole units.
function seconds(value: null | number): string {
  if (value === null) return "—";
  return value < 60 ? `${value.toFixed(1)}s` : formatDuration(value);
}

function secondsColumn<T>(key: keyof T & string, label: string) {
  return {
    format: (r: T) => seconds(r[key] as null | number),
    key,
    label,
    num: true,
    unit: "s",
  } satisfies ColumnSpec<T>;
}

function thinkTime(value: null | number): string {
  return value === null ? "—" : formatDuration(value);
}

const MODEL_COLUMNS: ColumnSpec<ModelRow>[] = [
  { key: "model", label: "model" },
  { key: "calls", label: "calls", num: true },
  secondsColumn<ModelRow>("p50", "p50"),
  secondsColumn<ModelRow>("p90", "p90"),
  secondsColumn<ModelRow>("p99", "p99"),
];

const TOOL_COLUMNS: ColumnSpec<ToolRow>[] = [
  { key: "name", label: "tool" },
  { key: "calls", label: "calls", num: true },
  secondsColumn<ToolRow>("p50", "p50"),
  secondsColumn<ToolRow>("p95", "p95"),
  secondsColumn<ToolRow>("total_s", "total"),
];

export function LatencyPanel({
  data,
}: Readonly<{ data: LatencyData }>): React.JSX.Element {
  const { daily, think } = data;
  const histogram = data.think_histogram.map((b) => {
    return {
      x: b.bucket,
      y: b.prompts,
    };
  });
  return (
    <section className="card" id="latency">
      <h2>Latency</h2>
      <ul aria-label="Think time" className="tiles">
        <li className="tile">
          <span className="tile-count hero">{thinkTime(think.p50)}</span>
          <span className="tile-label">p50 think time</span>
        </li>
        <li className="tile">
          <span className="tile-count">{thinkTime(think.p90)}</span>
          <span className="tile-label">p90 think time</span>
        </li>
        <li className="tile">
          <span className="tile-count">{formatCount(think.prompts)}</span>
          <span className="tile-label">prompts measured</span>
        </li>
      </ul>
      <p className="caption">{data.caption}</p>
      <LineChart
        format={seconds}
        label="Model latency per day"
        series={(["p50", "p90", "p99"] as const).map((q) => {
          return {
            label: q,
            points: daily.map((d) => ({ x: d.day, y: d[q] })),
          };
        })}
        titled
      />
      <ColumnChart
        columns={histogram}
        format={formatCount}
        label="Prompts per think time"
        titled
      />
      <DataTable<ModelRow>
        columns={MODEL_COLUMNS}
        id="models"
        meta={data._tables?.models}
        rowKey={(row) => row.model}
        rows={data.models}
        title="Model latency per model"
      />
      <DataTable<ToolRow>
        columns={TOOL_COLUMNS}
        id="tools"
        meta={data._tables?.tools}
        rowKey={(row) => row.name}
        rows={data.tools}
        title="Tool execution time per tool"
      />
    </section>
  );
}
