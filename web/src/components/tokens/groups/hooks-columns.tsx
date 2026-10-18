import type { ColumnSpec } from "../data-table.tsx";

import {
  formatCount,
  formatDuration,
  formatUsd,
} from "../../../lib/tokens-api.ts";

// One hook (hookName + script) and what it cost (see _hooks.py).
export interface HookRow {
  blocks: number;
  carry_usd: number;
  create_usd: number;
  errors: number;
  fires: number;
  hook: string;
  injected_usd: number;
  mean_ms: null | number;
  messages: number;
  retry_usd: number;
  runtime_s: number;
  script: string;
  tokens: number;
  total_usd: number;
}

export interface StopBounceRow {
  count: number;
  hook: string;
  retry_usd: number;
  script: string;
}

// One hook in the budget gate's last benchmark (see _hooks_budget.py).
export interface BudgetRow {
  budget_s: number;
  command: string;
  event: string;
  over_s: number;
  status: string;
  time_s: number;
}

const SECONDS_PER_MINUTE = 60;

export function formatSeconds(seconds: number): string {
  return seconds < SECONDS_PER_MINUTE
    ? `${seconds.toFixed(2)} s`
    : formatDuration(seconds);
}

function mono(text: string): React.JSX.Element {
  return <span className="mono">{text === "" ? "—" : text}</span>;
}

function usd<T>(
  key: keyof T & string,
  label: string,
  pick: (row: T) => number,
): ColumnSpec<T> {
  return {
    format: (r) => formatUsd(pick(r)),
    key,
    label,
    num: true,
    unit: "USD",
  };
}

function count<T>(
  key: keyof T & string,
  label: string,
  pick: (row: T) => number,
): ColumnSpec<T> {
  return { format: (r) => formatCount(pick(r)), key, label, num: true };
}

export const HOOK_COLUMNS: ColumnSpec<HookRow>[] = [
  { key: "hook", label: "hook" },
  { format: (r) => mono(r.script), key: "script", label: "script" },
  {
    format: (r) => <strong>{formatUsd(r.total_usd)}</strong>,
    key: "total_usd",
    label: "total $",
    num: true,
    unit: "USD",
  },
  count("fires", "fires", (r) => r.fires),
  {
    format: (r) => formatSeconds(r.runtime_s),
    key: "runtime_s",
    label: "runtime",
    num: true,
    unit: "s",
  },
  {
    format: (r) => (r.mean_ms === null ? "—" : `${r.mean_ms.toFixed(1)} ms`),
    key: "mean_ms",
    label: "mean",
    num: true,
    unit: "ms",
  },
  {
    format: (r) => formatCount(r.tokens),
    key: "tokens",
    label: "injected tokens",
    num: true,
    unit: "tokens (estimated)",
  },
  usd("injected_usd", "creation + carry $", (r) => r.injected_usd),
  count("blocks", "blocks", (r) => r.blocks),
  usd("retry_usd", "retry $", (r) => r.retry_usd),
  count("errors", "errors", (r) => r.errors),
  count("messages", "messages", (r) => r.messages),
];

export const STOP_COLUMNS: ColumnSpec<StopBounceRow>[] = [
  { key: "hook", label: "hook" },
  { format: (r) => mono(r.script), key: "script", label: "script" },
  count("count", "bounces", (r) => r.count),
  usd("retry_usd", "retry $", (r) => r.retry_usd),
];

export const BUDGET_COLUMNS: ColumnSpec<BudgetRow>[] = [
  { key: "event", label: "event" },
  { format: (r) => mono(r.command), key: "command", label: "command" },
  { key: "status", label: "status" },
  {
    format: (r) => formatSeconds(r.time_s),
    key: "time_s",
    label: "time",
    num: true,
    unit: "s",
  },
  {
    format: (r) => formatSeconds(r.budget_s),
    key: "budget_s",
    label: "budget",
    num: true,
    unit: "s",
  },
  {
    format: (r) => formatSeconds(r.over_s),
    key: "over_s",
    label: "over by",
    num: true,
    unit: "s",
  },
];
