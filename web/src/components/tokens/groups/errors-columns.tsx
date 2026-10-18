import type { ColumnSpec } from "../data-table.tsx";

import {
  formatCount,
  formatDay,
  formatShare,
} from "../../../lib/tokens-api.ts";

// Rows of the errors panel (see _errors.py).
export interface ApiErrorTypeRow {
  count: number;
  last_ts: number;
  sessions: number;
  type: string;
}

export interface ApiErrorRow {
  count: number;
  detail: string;
  last_ts: number;
  type: string;
}

export interface ErrorKindRow {
  count: number;
  error_kind: string;
  rate: number;
  share: number;
}

export interface ErrorToolRow {
  calls: number;
  error_rate: number;
  errors: number;
  family: string;
  name: string;
}

export interface RecentErrorRow {
  error_kind: string;
  family: string;
  key: string;
  name: string;
  target: string;
  ts: number;
}

function mono(text: string): React.JSX.Element {
  return <span className="mono">{text === "" ? "—" : text}</span>;
}

function count<T>(
  key: keyof T & string,
  label: string,
  pick: (row: T) => number,
): ColumnSpec<T> {
  return { format: (r) => formatCount(pick(r)), key, label, num: true };
}

function share<T>(
  key: keyof T & string,
  label: string,
  pick: (row: T) => number,
): ColumnSpec<T> {
  return {
    format: (r) => formatShare(pick(r)),
    key,
    label,
    num: true,
    unit: "share 0..1",
  };
}

function when<T>(
  key: keyof T & string,
  label: string,
  pick: (row: T) => number,
): ColumnSpec<T> {
  return { format: (r) => formatDay(pick(r)), key, label, unit: "epoch s" };
}

export const API_TYPE_COLUMNS: ColumnSpec<ApiErrorTypeRow>[] = [
  { key: "type", label: "type" },
  count("count", "count", (r) => r.count),
  count("sessions", "sessions", (r) => r.sessions),
  when("last_ts", "last", (r) => r.last_ts),
];

export const API_DETAIL_COLUMNS: ColumnSpec<ApiErrorRow>[] = [
  { key: "type", label: "type" },
  { format: (r) => mono(r.detail), key: "detail", label: "message" },
  count("count", "count", (r) => r.count),
  when("last_ts", "last", (r) => r.last_ts),
];

export const KIND_COLUMNS: ColumnSpec<ErrorKindRow>[] = [
  { format: (r) => mono(r.error_kind), key: "error_kind", label: "kind" },
  count("count", "errors", (r) => r.count),
  share("share", "of errors", (r) => r.share),
  share("rate", "of all calls", (r) => r.rate),
];

export const TOOL_COLUMNS: ColumnSpec<ErrorToolRow>[] = [
  { key: "name", label: "tool" },
  { format: (r) => mono(r.family), key: "family", label: "family" },
  count("errors", "errors", (r) => r.errors),
  count("calls", "calls", (r) => r.calls),
  share("error_rate", "error rate", (r) => r.error_rate),
];

export const RECENT_COLUMNS: ColumnSpec<RecentErrorRow>[] = [
  when("ts", "when", (r) => r.ts),
  { format: (r) => mono(r.key), key: "key", label: "session" },
  { key: "name", label: "tool" },
  { format: (r) => mono(r.family), key: "family", label: "family" },
  { format: (r) => mono(r.target), key: "target", label: "target" },
  { format: (r) => mono(r.error_kind), key: "error_kind", label: "kind" },
];
