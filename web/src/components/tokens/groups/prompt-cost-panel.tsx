import type { Tables } from "../../../lib/tokens-types.ts";

import {
  formatCount,
  formatDay,
  formatDuration,
  formatShare,
  formatUsd,
} from "../../../lib/tokens-api.ts";
import { ColumnChart } from "../column-chart.tsx";
import { type ColumnSpec, DataTable } from "../data-table.tsx";
import { LineChart } from "../line-chart.tsx";

// One user prompt and what it cost (see _prompt_cost.py).
export interface PromptCostRow {
  active_s: number;
  calls: number;
  idx: number;
  key: string;
  text: string;
  total: number;
  ts: number;
  // The cost on the scope's side: own, subagents, or both.
  usd: number;
  usd_own: number;
  usd_sub: number;
}

export interface PromptCostPanelData {
  _tables?: Tables;
  caption: string;
  daily: {
    day: string;
    mean_usd: number;
    median_usd: number;
    prompts: number;
    usd: number;
  }[];
  filtered_by: string;
  histogram: { bucket: string; prompts: number }[];
  prompts: PromptCostRow[];
  totals: {
    mean_usd: null | number;
    median_usd: null | number;
    prompts: number;
    top10_share: null | number;
    usd: number;
  };
}

function usdColumn(
  key: "total" | "usd" | "usd_own" | "usd_sub",
  label: string,
): ColumnSpec<PromptCostRow> {
  return {
    format: (r) => formatUsd(r[key]),
    key,
    label,
    num: true,
    unit: "USD",
  };
}

const COLUMNS: ColumnSpec<PromptCostRow>[] = [
  { format: (r) => formatDay(r.ts), key: "ts", label: "when" },
  {
    format: (r) => {
      return (
        <a href={`#/tokens/s/${encodeURIComponent(r.key)}`} title={r.text}>
          {r.text === "" ? "(no text)" : r.text.slice(0, 120)}
        </a>
      );
    },
    key: "text",
    label: "prompt",
  },
  {
    format: (r) => <strong>{formatUsd(r.usd)}</strong>,
    key: "usd",
    label: "USD (scope)",
    num: true,
    unit: "USD",
  },
  usdColumn("usd_own", "own"),
  usdColumn("usd_sub", "subagents"),
  usdColumn("total", "total"),
  {
    format: (r) => formatDuration(r.active_s),
    key: "active_s",
    label: "active",
    num: true,
    unit: "s",
  },
  { key: "calls", label: "calls", num: true },
  { key: "key", label: "session" },
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

export function PromptCostPanel({
  data,
}: Readonly<{ data: PromptCostPanelData }>): React.JSX.Element {
  const { totals } = data;
  return (
    <section className="card" id="prompts">
      <h2>Cost per user prompt</h2>
      <ul aria-label="Prompt cost summary" className="tiles">
        <Tile
          hero
          label="median per prompt"
          value={formatUsd(totals.median_usd)}
        />
        <Tile label="mean per prompt" value={formatUsd(totals.mean_usd)} />
        <Tile label="prompts" value={formatCount(totals.prompts)} />
        <Tile label="spent on them" value={formatUsd(totals.usd)} />
        <Tile
          label="costliest 10 prompts' share"
          value={formatShare(totals.top10_share)}
        />
      </ul>
      <p className="caption">{data.caption}</p>
      <p className="caption">Filtered by: {data.filtered_by}</p>
      <LineChart
        format={formatUsd}
        label="USD per prompt per day"
        series={[
          {
            label: "median",
            points: data.daily.map((d) => ({ x: d.day, y: d.median_usd })),
          },
          {
            label: "mean",
            points: data.daily.map((d) => ({ x: d.day, y: d.mean_usd })),
          },
        ]}
        titled
      />
      <ColumnChart
        columns={data.histogram.map((b) => ({ x: b.bucket, y: b.prompts }))}
        format={formatCount}
        label="Prompts by cost"
        titled
      />
      <DataTable<PromptCostRow>
        columns={COLUMNS}
        id="prompts"
        meta={data._tables?.prompts}
        rowKey={(row) => `${row.key}|${String(row.idx)}`}
        rows={data.prompts}
        title="Costliest prompts"
      />
    </section>
  );
}
