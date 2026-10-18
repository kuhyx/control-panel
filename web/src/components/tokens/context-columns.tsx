import { useState } from "react";

import type { ContextFileRow } from "../../lib/tokens-types.ts";
import type { ColumnSpec } from "./data-table.tsx";

import { optimisationPrompt, overLimit } from "../../lib/context-prompt.ts";
import { formatCount, formatUsd } from "../../lib/tokens-api.ts";

export function shortPath(path: string): string {
  return path.replace(/^\/home\/[^/]+/, "~");
}

const STATUS_CLASS: Record<ContextFileRow["status"], string> = {
  ok: "badge",
  "over budget": "badge warn-badge",
  "over hard limit": "badge bad-badge",
};

export const COLUMNS: ColumnSpec<ContextFileRow>[] = [
  {
    format: (f) => {
      return (
        <a className="mono" href={`#/tokens/f/${encodeURIComponent(f.path)}`}>
          {shortPath(f.path)}
        </a>
      );
    },
    key: "path",
    label: "file",
  },
  { key: "kind", label: "kind" },
  {
    format: (f) => {
      return (
        <span
          className={STATUS_CLASS[f.status]}
          title={f.breaches.map((b) => b.why).join("; ")}
        >
          {f.status}
        </span>
      );
    },
    key: "status",
    label: "status",
  },
  {
    format: (f) => (f.lines === null ? "—" : formatCount(f.lines)),
    key: "lines",
    label: "lines",
    num: true,
  },
  {
    format: (f) => (f.bytes === null ? "gone" : formatCount(f.bytes)),
    key: "bytes",
    label: "bytes",
    num: true,
    unit: "bytes",
  },
  {
    format: (f) => formatCount(f.tokens),
    key: "tokens",
    label: "tokens loaded",
    num: true,
    unit: "tokens (bytes/4)",
  },
  {
    format: (f) => <strong>{formatUsd(f.usd_per_day)}</strong>,
    key: "usd_per_day",
    label: "$/day",
    num: true,
    unit: "USD/day",
  },
  {
    format: (f) => f.hard_limits.join("; ") || "—",
    key: "hard_limits",
    label: "hard limits",
  },
  {
    format: (f) => f.budgets.join("; ") || "—",
    key: "budgets",
    label: "budgets",
  },
  {
    format: (f) => `${String(f.history.length)} points`,
    key: "history",
    label: "history",
    num: true,
  },
];

export function OptimiseButton({
  measure,
  rows,
  selected,
}: Readonly<{
  measure: string;
  rows: ContextFileRow[];
  selected: ContextFileRow[];
}>): React.JSX.Element {
  const [status, setStatus] = useState("");
  const chosen = selected.length > 0 ? selected : overLimit(rows);
  return (
    <p className="table-toolbar">
      <button
        className="table-button"
        disabled={chosen.length === 0}
        onClick={() => {
          void navigator.clipboard
            .writeText(optimisationPrompt(chosen, measure))
            .then(() => {
              setStatus(`prompt for ${String(chosen.length)} files copied`);
            })
            .catch(() => {
              setStatus("clipboard unavailable");
            });
        }}
        type="button"
      >
        Copy optimisation prompt ({chosen.length}{" "}
        {selected.length > 0 ? "selected" : "over limit"})
      </button>
      <span aria-live="polite" className="category">
        {status}
      </span>
    </p>
  );
}
