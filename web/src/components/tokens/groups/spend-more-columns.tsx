import type { Tables } from "../../../lib/tokens-types.ts";
import type { ColumnSpec } from "../data-table.tsx";

import { formatDay } from "../../../lib/tokens-api.ts";
import { type HeatCell, WEEKDAYS } from "./spend-more-heatmap.tsx";
import {
  countColumn,
  monoColumn,
  shareColumn,
  textColumn,
  usdColumn,
} from "./tools-columns.tsx";

export interface MonthRow {
  calls: number;
  month: string;
  usd: number;
}

export interface CumulativeRow {
  cum_usd: number;
  dom: number;
  month: string;
  usd: number;
}

export interface ModelRow {
  calls: number;
  model: string;
  share: null | number;
  usd: number;
}

export type CwdRow = Omit<ModelRow, "model"> & { cwd: string };

export interface BlockRow {
  calls: number;
  day: string;
  end: number;
  first_ts: number;
  last_ts: number;
  start: number;
  usd: number;
  usd_per_hour: null | number;
}

export interface BlockDayRow {
  blocks: number;
  day: string;
  max_block_usd: number;
}

export interface RateLimitRow {
  day: string;
  errors: number;
}

export interface SpendMoreData {
  _tables?: Tables;
  block_daily: BlockDayRow[];
  blocks: BlockRow[];
  by_cwd: CwdRow[];
  by_model: ModelRow[];
  caption: string;
  cumulative: CumulativeRow[];
  // 7 x 24 USD, Monday first: the whole grid, never cut by the table layer.
  grid: number[][];
  heatmap: HeatCell[];
  months: MonthRow[];
  rate_limits: RateLimitRow[];
  totals: {
    blocks: number;
    peak_block_usd: number;
    rate_limit_errors: number;
    usd: number;
  };
}

export const MONTH_COLUMNS: ColumnSpec<MonthRow>[] = [
  textColumn<MonthRow>("month", "month"),
  usdColumn<MonthRow>("usd", "USD"),
  countColumn<MonthRow>("calls", "calls"),
];

export const MODEL_COLUMNS: ColumnSpec<ModelRow>[] = [
  textColumn<ModelRow>("model", "model"),
  usdColumn<ModelRow>("usd", "USD"),
  shareColumn<ModelRow>("share", "share"),
  countColumn<ModelRow>("calls", "calls"),
];

export const CWD_COLUMNS: ColumnSpec<CwdRow>[] = [
  monoColumn<CwdRow>("cwd", "repo / cwd"),
  usdColumn<CwdRow>("usd", "USD"),
  shareColumn<CwdRow>("share", "share"),
  countColumn<CwdRow>("calls", "calls"),
];

export const HEAT_COLUMNS: ColumnSpec<HeatCell>[] = [
  {
    format: (r) => WEEKDAYS[r.weekday],
    key: "weekday",
    label: "weekday",
  },
  countColumn<HeatCell>("hour", "hour", "local hour 0..23"),
  usdColumn<HeatCell>("usd", "USD"),
  countColumn<HeatCell>("calls", "calls"),
];

export const BLOCK_COLUMNS: ColumnSpec<BlockRow>[] = [
  {
    format: (r) => formatDay(r.start),
    key: "start",
    label: "block start",
    num: true,
    unit: "unix s",
  },
  usdColumn<BlockRow>("usd", "USD"),
  countColumn<BlockRow>("calls", "calls"),
  usdColumn<BlockRow>("usd_per_hour", "USD / active hour"),
];

export const BLOCK_DAY_COLUMNS: ColumnSpec<BlockDayRow>[] = [
  textColumn<BlockDayRow>("day", "day"),
  countColumn<BlockDayRow>("blocks", "blocks"),
  usdColumn<BlockDayRow>("max_block_usd", "costliest block"),
];

export const RATE_COLUMNS: ColumnSpec<RateLimitRow>[] = [
  textColumn<RateLimitRow>("day", "day"),
  countColumn<RateLimitRow>("errors", "rate-limit errors"),
];
