import type { Tables } from "./tokens-types.ts";

// Context-files panel types (re-exported by tokens-types.ts).
export interface Breach {
  hard: boolean;
  limit: number;
  measure: string;
  value: number;
  why: string;
}

export interface ContextFileRow {
  breaches: Breach[];
  budgets: string[];
  bytes: null | number;
  hard_limits: string[];
  history: { bytes: number; source: string; ts: number }[];
  kind: string;
  lines: null | number;
  path: string;
  standing: string;
  status: "ok" | "over budget" | "over hard limit";
  tokens: number;
  usd_per_day: number;
  warning: null | string;
}

export interface ContextPanel {
  _tables?: Tables;
  calls_per_day: number;
  files: ContextFileRow[];
  measure_command: string;
  price_per_mtok: number;
}

export interface ContextFileDetail {
  content: null | string;
  git_log: string[];
  kind: string;
  path: string;
}
