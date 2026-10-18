import type { ColumnSpec } from "../data-table.tsx";

import {
  formatCount,
  formatShare,
  formatUsd,
} from "../../../lib/tokens-api.ts";

// Column builders shared by the tools / subagents / session-stats / anomalies /
// prompt-habits / spend-more panels: one place decides how a USD, count or
// share cell looks, and every numeric column names its unit for copy/export.

type Key<T> = keyof T & string;

function numberOf(value: unknown): null | number {
  return typeof value === "number" ? value : null;
}

export function textColumn<T>(key: Key<T>, label: string): ColumnSpec<T> {
  return { key, label };
}

export function monoColumn<T>(key: Key<T>, label: string): ColumnSpec<T> {
  return {
    format: (row) => <span className="mono">{String(row[key])}</span>,
    key,
    label,
  };
}

export function usdColumn<T>(key: Key<T>, label: string): ColumnSpec<T> {
  return {
    format: (row) => formatUsd(numberOf(row[key])),
    key,
    label,
    num: true,
    unit: "USD",
  };
}

export function countColumn<T>(
  key: Key<T>,
  label: string,
  unit?: string,
): ColumnSpec<T> {
  return {
    format: (row) => {
      const value = numberOf(row[key]);
      return value === null ? "—" : formatCount(value);
    },
    key,
    label,
    num: true,
    ...(unit !== undefined && { unit }),
  };
}

export function shareColumn<T>(key: Key<T>, label: string): ColumnSpec<T> {
  return {
    format: (row) => formatShare(numberOf(row[key])),
    key,
    label,
    num: true,
    unit: "share 0..1",
  };
}
