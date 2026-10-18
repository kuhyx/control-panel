import type { Tables } from "../../../lib/tokens-types.ts";

import {
  formatCount,
  formatDay,
  formatShare,
  formatUsd,
} from "../../../lib/tokens-api.ts";
import { type ColumnSpec, DataTable } from "../data-table.tsx";

export interface ClassDay {
  cache_read: number;
  cache_read_usd: number;
  cold_starts: number;
  cw_1h: number;
  cw_1h_usd: number;
  cw_5m: number;
  cw_5m_usd: number;
  day: string;
  hit_ratio: null | number;
  input: number;
  input_usd: number;
  output: number;
  output_usd: number;
  spend_usd: number;
  unsplit: number;
  unsplit_usd: number;
  usd: number;
  waste_usd: number;
}

export interface WasteRow {
  cold_start_usd: number;
  cold_starts: number;
  key: string;
  wasted_calls: number;
  wasted_tokens: number;
  wasted_usd: number;
}

export interface CompactionRow {
  count: number;
  duration_s: number;
  est_usd: number;
  key: string;
  model: string;
  post_tokens: number;
  pre_tokens: number;
  trigger: string;
  ts: number;
}

function usd<T>(key: keyof T & string, label: string, get: (r: T) => number) {
  return {
    format: (r: T) => formatUsd(get(r)),
    key,
    label,
    num: true,
    unit: "USD",
  } satisfies ColumnSpec<T>;
}

function count<T>(key: keyof T & string, label: string, get: (r: T) => number) {
  return {
    format: (r: T) => formatCount(get(r)),
    key,
    label,
    num: true,
    unit: "tokens",
  } satisfies ColumnSpec<T>;
}

const DAY_COLUMNS: ColumnSpec<ClassDay>[] = [
  { key: "day", label: "day" },
  count("input", "input", (r) => r.input),
  count("cw_5m", "write 5m", (r) => r.cw_5m),
  count("cw_1h", "write 1h", (r) => r.cw_1h),
  count("unsplit", "write unsplit", (r) => r.unsplit),
  count("cache_read", "cache read", (r) => r.cache_read),
  count("output", "output", (r) => r.output),
  usd("usd", "classes $", (r) => r.usd),
  usd("spend_usd", "recorded $", (r) => r.spend_usd),
  {
    format: (r) => formatShare(r.hit_ratio),
    key: "hit_ratio",
    label: "hit ratio",
    num: true,
    unit: "share 0..1",
  },
  usd("waste_usd", "waste $", (r) => r.waste_usd),
  { key: "cold_starts", label: "cold starts", num: true },
];

const WASTE_COLUMNS: ColumnSpec<WasteRow>[] = [
  {
    format: (r) => <span className="mono">{r.key}</span>,
    key: "key",
    label: "key",
  },
  usd("wasted_usd", "waste $", (r) => r.wasted_usd),
  count("wasted_tokens", "wasted tokens", (r) => r.wasted_tokens),
  { key: "wasted_calls", label: "wasted writes", num: true },
  { key: "cold_starts", label: "cold starts", num: true },
  usd("cold_start_usd", "cold-start $", (r) => r.cold_start_usd),
];

const COMPACTION_COLUMNS: ColumnSpec<CompactionRow>[] = [
  { format: (r) => formatDay(r.ts), key: "ts", label: "when" },
  {
    format: (r) => <span className="mono">{r.key}</span>,
    key: "key",
    label: "key",
  },
  { key: "model", label: "model" },
  { key: "trigger", label: "trigger" },
  { key: "count", label: "events", num: true },
  count("pre_tokens", "pre tokens", (r) => r.pre_tokens),
  count("post_tokens", "post tokens", (r) => r.post_tokens),
  { key: "duration_s", label: "duration", num: true, unit: "s" },
  usd("est_usd", "est. $", (r) => r.est_usd),
];

export function ClassTables({
  compactions,
  daily,
  tables,
  waste,
}: Readonly<{
  compactions: CompactionRow[];
  daily: ClassDay[];
  tables: Tables | undefined;
  waste: WasteRow[];
}>): React.JSX.Element {
  return (
    <>
      <DataTable<WasteRow>
        columns={WASTE_COLUMNS}
        id="waste"
        meta={tables?.waste}
        rowKey={(row) => row.key}
        rows={waste}
        title="Cache writes never re-read, and cold starts, per key"
      />
      <DataTable<CompactionRow>
        columns={COMPACTION_COLUMNS}
        id="compactions"
        meta={tables?.compactions}
        rowKey={(row, index) => `${row.key}|${String(row.ts)}|${String(index)}`}
        rows={compactions}
        title="Compactions (cost estimated)"
      />
      <DataTable<ClassDay>
        columns={DAY_COLUMNS}
        id="daily"
        meta={tables?.daily}
        rowKey={(row) => row.day}
        rows={daily}
        title="Per day, every class"
      />
    </>
  );
}
