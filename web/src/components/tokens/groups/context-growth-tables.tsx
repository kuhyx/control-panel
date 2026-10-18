import type { Tables } from "../../../lib/tokens-types.ts";

import { formatCount, formatDay, formatUsd } from "../../../lib/tokens-api.ts";
import { type ColumnSpec, DataTable } from "../data-table.tsx";

export interface CrossingRow {
  calls: number;
  calls_over_250k: number;
  calls_over_300k: number;
  key: string;
  max_context: number;
  title: string;
  usd: number;
  usd_over_300k: number;
}

export interface HandoffRow {
  detail: string;
  key: string;
  source: string;
  ts: number;
}

function mono(text: string): React.JSX.Element {
  return <span className="mono">{text}</span>;
}

const CROSSING_COLUMNS: ColumnSpec<CrossingRow>[] = [
  { format: (r) => mono(r.key), key: "key", label: "key" },
  {
    format: (r) => (r.title === "" ? "—" : r.title),
    key: "title",
    label: "title",
  },
  {
    format: (r) => formatCount(r.max_context),
    key: "max_context",
    label: "max context",
    num: true,
    unit: "tokens",
  },
  { key: "calls", label: "calls", num: true },
  { key: "calls_over_250k", label: "calls > 250k", num: true },
  { key: "calls_over_300k", label: "calls > 300k", num: true },
  {
    format: (r) => <strong>{formatUsd(r.usd_over_300k)}</strong>,
    key: "usd_over_300k",
    label: "$ of calls > 300k",
    num: true,
    unit: "USD",
  },
  {
    format: (r) => formatUsd(r.usd),
    key: "usd",
    label: "key $",
    num: true,
    unit: "USD",
  },
];

const HANDOFF_COLUMNS: ColumnSpec<HandoffRow>[] = [
  { format: (r) => formatDay(r.ts), key: "ts", label: "when" },
  { format: (r) => mono(r.key), key: "key", label: "key" },
  { key: "source", label: "seen as" },
  { format: (r) => mono(r.detail), key: "detail", label: "path / prompt" },
];

export function GrowthTables({
  crossings,
  handoffs,
  tables,
}: Readonly<{
  crossings: CrossingRow[];
  handoffs: HandoffRow[];
  tables: Tables | undefined;
}>): React.JSX.Element {
  return (
    <>
      <DataTable<CrossingRow>
        columns={CROSSING_COLUMNS}
        id="crossings"
        meta={tables?.crossings}
        rowKey={(row) => row.key}
        rows={crossings}
        title="Keys that crossed 250k"
      />
      <DataTable<HandoffRow>
        columns={HANDOFF_COLUMNS}
        id="handoffs"
        meta={tables?.handoffs}
        rowKey={(row, index) => `${row.key}|${String(row.ts)}|${String(index)}`}
        rows={handoffs}
        title="Handoffs (written, picked up, or named by a hook)"
      />
    </>
  );
}
