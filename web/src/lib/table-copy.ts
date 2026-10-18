// What "Copy for Claude" / "Copy as JSON" put on the clipboard: a compact
// markdown table under one header line naming the view, the filters, the
// window and the units, so a pasted table is never read without its scope.
import type { TokenQuery } from "./tokens-api.ts";

import { describeTable, type TableState } from "./table-parameters.ts";

export interface CopyColumn {
  key: string;
  label: string;
  unit?: string;
}

export interface CopyContext {
  matched: null | number;
  query: null | TokenQuery;
  selected: boolean;
  state: TableState;
  title: string;
  view: string;
  window: null | { since: number; until: number };
}

function day(epochSeconds: number): string {
  const when = new Date(epochSeconds * 1000);
  return when.toISOString().slice(0, 10);
}

function compact(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "number") {
    return String(
      Number.isSafeInteger(value) ? value : Number(value.toPrecision(4)),
    );
  }
  const text = typeof value === "string" ? value : JSON.stringify(value);
  const oneLine = text
    .split("\n")
    .map((line) => line.trim())
    .join(" ");
  return oneLine.replaceAll("|", String.raw`\|`);
}

export function describeFilters(query: null | TokenQuery): string {
  if (query === null) return "none";
  const parts = (["cwd", "model", "from", "to", "window"] as const)
    .filter((key) => query[key] !== "")
    .map((key) => `${key}=${query[key]}`);
  if (query.scope !== "all") parts.push(`scope=${query.scope}`);
  return parts.length === 0 ? "none" : parts.join(", ");
}

export function copyHeader(
  columns: CopyColumn[],
  rows: number,
  context: CopyContext,
): string {
  const window =
    context.window === null
      ? "n/a"
      : `${day(context.window.since)} → ${day(context.window.until)}`;
  const units = columns
    .filter((c): c is CopyColumn & { unit: string } => c.unit !== undefined)
    .map((c) => `${c.key}=${c.unit}`)
    .join(", ");
  const which = context.selected
    ? `${String(rows)} selected rows`
    : `${String(rows)} of ${String(context.matched ?? rows)} matching rows`;
  return [
    `View: ${context.view} / ${context.title}`,
    `window ${window}`,
    `filters: ${describeFilters(context.query)}`,
    `table: ${describeTable(context.state)}`,
    which,
    `units: ${units === "" ? "as labelled" : units}; USD = API list price`,
  ].join(" · ");
}

export function markdownTable(columns: CopyColumn[], rows: object[]): string {
  const head = `| ${columns.map((c) => c.label).join(" | ")} |`;
  const rule = `|${columns.map(() => "---").join("|")}|`;
  const body = rows.map((row) => {
    const record = row as Record<string, unknown>;
    return `| ${columns.map((c) => compact(record[c.key])).join(" | ")} |`;
  });
  return [head, rule, ...body].join("\n");
}

export function forClaude(
  columns: CopyColumn[],
  rows: object[],
  context: CopyContext,
): string {
  return `${copyHeader(columns, rows.length, context)}\n\n${markdownTable(columns, rows)}\n`;
}

export function asJson(
  columns: CopyColumn[],
  rows: object[],
  context: CopyContext,
): string {
  return JSON.stringify(
    { header: copyHeader(columns, rows.length, context), rows },
    null,
    1,
  );
}
