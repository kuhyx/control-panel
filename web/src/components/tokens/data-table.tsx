import { useState } from "react";

import type { ColumnMeta } from "./table-filters.tsx";

import { asJson, type CopyContext, forClaude } from "../../lib/table-copy.ts";
import { toCsv } from "./csv.tsx";
import { TableHead } from "./table-head.tsx";
import { useScope, useTableState } from "./table-scope.tsx";
import { type Counts, TableToolbar } from "./table-toolbar.tsx";

export interface ColumnSpec<T> {
  // Cell content; defaults to the raw value ("—" when null).
  format?: (row: T) => React.ReactNode;
  key: keyof T & string;
  label: string;
  // Right-aligned, tabular figures.
  num?: boolean;
  // Unit named in the copied header (USD, tokens, s, share 0..1, …).
  unit?: string;
}

// What the backend's table layer reports for one table (see _tables.py).
export interface TableMeta {
  columns: Record<string, ColumnMeta>;
  matched: number;
  shown: number;
  total: number;
}

// Longer text is cut in the cell (full text on hover, and in every export).
const MAX_CELL = 120;

function plain(value: unknown): React.JSX.Element {
  if (value === null || value === undefined) return <>—</>;
  if (typeof value === "number") return <>{value.toLocaleString("en-US")}</>;
  const text = typeof value === "string" ? value : JSON.stringify(value);
  const isLong = text.length > MAX_CELL;
  return (
    <span title={isLong ? text : undefined}>
      {isLong ? `${text.slice(0, MAX_CELL)}…` : text}
    </span>
  );
}

// The one table component every /tokens table uses: search, per-column
// filters and multi-key sort (applied by the backend, state in the URL hash),
// row selection, Copy for Claude / Copy as JSON / CSV, and "Show all".
export function DataTable<T extends object>({
  actions,
  caption,
  columns,
  id,
  meta,
  rowKey,
  rows,
  title,
}: Readonly<{
  // Extra toolbar buttons, given the selected rows (empty: none selected).
  actions?: (selected: T[]) => React.ReactNode;
  caption?: React.ReactNode;
  columns: ColumnSpec<T>[];
  id: string;
  meta?: TableMeta | undefined;
  rowKey: (row: T, index: number) => string;
  rows: T[];
  title: React.ReactNode;
}>): React.JSX.Element {
  const scope = useScope();
  const [state, setState] = useTableState(id);
  const [selected, setSelected] = useState<ReadonlySet<string>>(new Set());
  const keyed = rows.map((row, index) => ({ key: rowKey(row, index), row }));
  const keys = keyed.map((k) => k.key);
  const picked = keyed.filter((k) => selected.has(k.key)).map((k) => k.row);
  const chosen = picked.length > 0 ? picked : rows;
  const counts: Counts = meta ?? {
    matched: rows.length,
    shown: rows.length,
    total: rows.length,
  };
  // Nothing selected and the table is cut by its limit: copy every matching
  // row (nested tables such as prompts.tools copy their own list).
  const copyRows = async (): Promise<object[]> => {
    const loadAll = scope?.loadAll;
    const isNested = id.includes(".");
    const isCut = counts.shown < counts.matched;
    const isWhole = isNested || !isCut || picked.length > 0;
    return isWhole || loadAll === undefined ? chosen : loadAll(id);
  };
  const context: CopyContext = {
    matched: counts.matched,
    query: scope?.query ?? null,
    selected: picked.length > 0,
    state,
    title: typeof title === "string" ? title : id,
    view: scope?.title ?? id,
    window: scope?.window ?? null,
  };
  const csv = `data:text/csv;charset=utf-8,${encodeURIComponent(
    toCsv(
      chosen,
      columns.map((c) => c.key),
    ),
  )}`;
  return (
    <div className="data-table">
      <h3>{title}</h3>
      {caption}
      <TableToolbar
        counts={counts}
        csvHref={csv}
        csvName={`${id}.csv`}
        forClaude={async () => forClaude(columns, await copyRows(), context)}
        json={async () => asJson(columns, await copyRows(), context)}
        onSearch={(q) => {
          setState({ ...state, q });
        }}
        onShowAll={() => {
          setState({ ...state, limit: 0 });
        }}
        search={state.q}
        selected={picked.length}
      />
      {actions?.(picked)}
      <div className="table-scroll">
        <table className="table tokens-table">
          <TableHead
            allSelected={rows.length > 0 && picked.length === rows.length}
            columns={columns}
            meta={meta?.columns ?? {}}
            onSelectAll={(all) => {
              setSelected(new Set(all ? keys : []));
            }}
            onState={setState}
            state={state}
          />
          <tbody>
            {keyed.map(({ key, row }) => {
              return (
                <tr
                  className={selected.has(key) ? "selected" : undefined}
                  key={key}
                >
                  <td>
                    <input
                      aria-label={`select ${key}`}
                      checked={selected.has(key)}
                      onChange={(event) => {
                        const next = new Set(selected);
                        if (event.target.checked) next.add(key);
                        else next.delete(key);
                        setSelected(next);
                      }}
                      type="checkbox"
                    />
                  </td>
                  {columns.map((c) => {
                    return (
                      <td
                        className={c.num === true ? "num" : undefined}
                        key={c.key}
                      >
                        {c.format === undefined
                          ? plain(row[c.key])
                          : c.format(row)}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
        {rows.length === 0 && <p className="empty">No rows match.</p>}
      </div>
    </div>
  );
}
