import type { Tables } from "../../../lib/tokens-types.ts";

import {
  formatCount,
  formatDay,
  formatShare,
  formatUsd,
} from "../../../lib/tokens-api.ts";
import { type ColumnSpec, DataTable } from "../data-table.tsx";
import { LineChart } from "../line-chart.tsx";

interface Split {
  output: number;
  output_usd: number;
  text: number;
  think: number;
  tool: number;
}

type OutputDay = Split & {
  day: string;
  output_share: null | number;
  spend_usd: number;
};

interface LongestRow {
  key: string;
  model: string;
  output: number;
  output_usd: number;
  text: null | number;
  think: null | number;
  tool: null | number;
  ts: number;
  usd: number;
}

export interface OutputData {
  _tables?: Tables;
  caption: string;
  daily: OutputDay[];
  longest: LongestRow[];
  totals: Split & { output_share: null | number; spend_usd: number };
}

function tokens(value: null | number): string {
  return value === null ? "—" : formatCount(value);
}

function splitColumn(
  key: "text" | "think" | "tool",
  label: string,
): ColumnSpec<LongestRow> {
  return {
    format: (r) => tokens(r[key]),
    key,
    label,
    num: true,
    unit: "tokens (estimated)",
  };
}

const LONGEST_COLUMNS: ColumnSpec<LongestRow>[] = [
  { format: (r) => formatDay(r.ts), key: "ts", label: "when" },
  {
    format: (r) => <span className="mono">{r.key}</span>,
    key: "key",
    label: "key",
  },
  { key: "model", label: "model" },
  {
    format: (r) => <strong>{formatCount(r.output)}</strong>,
    key: "output",
    label: "output",
    num: true,
    unit: "tokens",
  },
  {
    format: (r) => formatUsd(r.output_usd),
    key: "output_usd",
    label: "output $",
    num: true,
    unit: "USD",
  },
  {
    format: (r) => formatUsd(r.usd),
    key: "usd",
    label: "call $",
    num: true,
    unit: "USD",
  },
  splitColumn("think", "thinking"),
  splitColumn("text", "text"),
  splitColumn("tool", "tool calls"),
];

export function OutputPanel({
  data,
}: Readonly<{ data: OutputData }>): React.JSX.Element {
  const { daily, totals } = data;
  const thinking = totals.output > 0 ? totals.think / totals.output : null;
  return (
    <section className="card" id="output">
      <h2>Output</h2>
      <ul aria-label="Output summary" className="tiles">
        <li className="tile">
          <span className="tile-count hero">
            {formatUsd(totals.output_usd)}
          </span>
          <span className="tile-label">
            output ({formatCount(totals.output)} tokens)
          </span>
        </li>
        <li className="tile">
          <span className="tile-count">{formatShare(totals.output_share)}</span>
          <span className="tile-label">
            of {formatUsd(totals.spend_usd)} spend
          </span>
        </li>
        <li className="tile">
          <span className="tile-count">{formatShare(thinking)}</span>
          <span className="tile-label">of output is thinking (est.)</span>
        </li>
      </ul>
      <p className="caption">{data.caption}</p>
      <LineChart
        format={formatCount}
        label="Output tokens per day"
        series={[
          {
            label: "thinking",
            points: daily.map((d) => ({ x: d.day, y: d.think })),
          },
          {
            label: "text",
            points: daily.map((d) => ({ x: d.day, y: d.text })),
          },
          {
            label: "tool calls",
            points: daily.map((d) => ({ x: d.day, y: d.tool })),
          },
        ]}
      />
      <LineChart
        format={formatShare}
        label="Output share of spend per day"
        series={[
          {
            label: "output $ / spend",
            points: daily.map((d) => ({ x: d.day, y: d.output_share })),
          },
        ]}
      />
      <DataTable<LongestRow>
        columns={LONGEST_COLUMNS}
        id="longest"
        meta={data._tables?.longest}
        rowKey={(row, index) => `${row.key}|${String(row.ts)}|${String(index)}`}
        rows={data.longest}
        title="Longest replies"
      />
    </section>
  );
}
