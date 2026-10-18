import type { Tables } from "../../../lib/tokens-types.ts";

import { formatCount, formatUsd } from "../../../lib/tokens-api.ts";
import { type ColumnSpec, DataTable } from "../data-table.tsx";

// One chunk of context and what it cost: creation + carry (see _carry.py).
export interface ChunkRow {
  carried_calls?: number;
  carry_usd: number;
  count: number;
  create_usd: number;
  detail: string;
  label: string;
  tokens: number;
  total_usd: number;
}

export const CHUNK_COLUMNS: ColumnSpec<ChunkRow>[] = [
  { key: "label", label: "what" },
  {
    format: (r) => <span className="mono">{r.detail === "" ? "—" : r.detail}</span>,
    key: "detail",
    label: "detail",
  },
  {
    format: (r) => <strong>{formatUsd(r.total_usd)}</strong>,
    key: "total_usd",
    label: "total $",
    num: true,
    unit: "USD",
  },
  {
    format: (r) => formatUsd(r.create_usd),
    key: "create_usd",
    label: "creation $",
    num: true,
    unit: "USD",
  },
  {
    format: (r) => formatUsd(r.carry_usd),
    key: "carry_usd",
    label: "carry $",
    num: true,
    unit: "USD",
  },
  {
    format: (r) => formatCount(r.tokens),
    key: "tokens",
    label: "tokens",
    num: true,
    unit: "tokens (estimated)",
  },
  {
    format: (r) => formatCount(r.count),
    key: "count",
    label: "count",
    num: true,
  },
];

// A titled table of chunk rows, keyed by its panel-relative table id.
export function ChunkTable({
  id,
  rows,
  tables,
  title,
  withCalls = false,
}: Readonly<{
  id: string;
  rows: ChunkRow[];
  tables: Tables | undefined;
  title: string;
  withCalls?: boolean;
}>): React.JSX.Element {
  const columns: ColumnSpec<ChunkRow>[] = withCalls
    ? [
        ...CHUNK_COLUMNS,
        { key: "carried_calls", label: "calls carried (avg)", num: true },
      ]
    : CHUNK_COLUMNS;
  return (
    <DataTable<ChunkRow>
      columns={columns}
      id={id}
      meta={tables?.[id]}
      rowKey={(row, index) => `${row.label}|${row.detail}|${String(index)}`}
      rows={rows}
      title={title}
    />
  );
}
