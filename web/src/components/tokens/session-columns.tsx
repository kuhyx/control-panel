import type {
  PromptRow,
  SubagentRow,
  ToolRow,
} from "../../lib/tokens-types.ts";
import type { ColumnSpec } from "./data-table.tsx";

import {
  formatCount,
  formatDay,
  formatDuration,
  formatShare,
  formatUsd,
} from "../../lib/tokens-api.ts";

export const SUBAGENT_COLUMNS: ColumnSpec<SubagentRow>[] = [
  {
    format: (a) =>
      `${a.depth > 1 ? "↳ ".repeat(a.depth - 1) : ""}${a.description}`,
    key: "description",
    label: "subagent",
  },
  { key: "agent_type", label: "type" },
  {
    format: (a) => a.model.replace(/^claude-/, ""),
    key: "model",
    label: "model",
  },
  {
    format: (a) => <strong>{formatUsd(a.usd)}</strong>,
    key: "usd",
    label: "USD",
    num: true,
    unit: "USD",
  },
  {
    format: (a) => formatDuration(a.wall_s),
    key: "wall_s",
    label: "wall",
    num: true,
    unit: "s",
  },
  {
    format: (a) => formatDuration(a.active_s),
    key: "active_s",
    label: "active",
    num: true,
    unit: "s",
  },
  {
    format: (a) => formatCount(a.calls),
    key: "calls",
    label: "calls",
    num: true,
  },
];

export const TOOL_COLUMNS: ColumnSpec<ToolRow>[] = [
  {
    format: (t) => <span className="mono">{t.name}</span>,
    key: "name",
    label: "tool",
  },
  {
    format: (t) => formatCount(t.calls),
    key: "calls",
    label: "calls",
    num: true,
  },
  {
    format: (t) => formatCount(t.result_tokens),
    key: "result_tokens",
    label: "result tokens",
    num: true,
    unit: "tokens",
  },
  {
    format: (t) => formatUsd(t.usd),
    key: "usd",
    label: "USD (issuing calls)",
    num: true,
    unit: "USD",
  },
  {
    format: (t) => formatShare(t.share),
    key: "share",
    label: "share of prompt",
    num: true,
    unit: "share",
  },
  {
    format: (t) => formatUsd(t.carry_usd),
    key: "carry_usd",
    label: "carry USD",
    num: true,
    unit: "USD",
  },
];

export const PROMPT_COLUMNS: ColumnSpec<PromptRow>[] = [
  { format: (p) => formatDay(p.ts), key: "ts", label: "when", unit: "unix s" },
  {
    format: (p) => <a href={`#prompt-${String(p.idx)}`}>{p.text}</a>,
    key: "text",
    label: "prompt",
  },
  {
    format: (p) => <strong>{formatUsd(p.usd)}</strong>,
    key: "usd",
    label: "USD",
    num: true,
    unit: "USD",
  },
  {
    format: (p) => formatUsd(p.usd_own),
    key: "usd_own",
    label: "own",
    num: true,
    unit: "USD",
  },
  {
    format: (p) => formatUsd(p.usd_sub),
    key: "usd_sub",
    label: "agents",
    num: true,
    unit: "USD",
  },
  {
    format: (p) => formatDuration(p.active_s),
    key: "active_s",
    label: "active",
    num: true,
    unit: "s",
  },
  { key: "calls", label: "calls", num: true },
];
