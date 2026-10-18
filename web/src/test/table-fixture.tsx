// Shared rows, columns and wrappers for the DataTable tests.
import { type Mock, vi } from "vitest";

import {
  type ColumnSpec,
  DataTable,
  type TableMeta,
} from "../components/tokens/data-table.tsx";
import { TableScope } from "../components/tokens/table-scope.tsx";
import { EMPTY_QUERY, type TokenQuery } from "../lib/tokens-api.ts";

export interface Row {
  kind: string;
  label: null | string;
  n: number;
  obj: { a: number };
}

export const ROWS: Row[] = [
  { kind: "tool", label: "alpha", n: 1234, obj: { a: 1 } },
  { kind: "mark", label: null, n: 5, obj: { a: 2 } },
];

export const COLUMNS: ColumnSpec<Row>[] = [
  { key: "label", label: "label" },
  { key: "n", label: "n", num: true, unit: "USD" },
  { key: "kind", label: "kind" },
  { format: (row) => `#${String(row.obj.a)}`, key: "obj", label: "obj" },
];

export const META: TableMeta = {
  columns: {
    kind: { kind: "enum", values: ["mark", "tool"] },
    label: { kind: "text" },
    n: { kind: "number" },
    obj: { kind: "object" },
  },
  matched: 5,
  shown: 2,
  total: 9,
};

export function table(
  rows: Row[] = ROWS,
  meta: null | TableMeta = META,
): React.JSX.Element {
  return (
    <DataTable<Row>
      actions={(selected) => <span>picked {selected.length}</span>}
      columns={COLUMNS}
      id="rows"
      meta={meta ?? undefined}
      rowKey={(row) => String(row.n)}
      rows={rows}
      title="Things"
    />
  );
}

export function scoped(
  onQuery: (q: TokenQuery) => void,
  tables = {},
): React.JSX.Element {
  const scope = {
    onQuery,
    panel: "demo",
    query: { ...EMPTY_QUERY, cwd: "/r", tables },
    title: "Demo",
    window: { since: 1_760_000_000, until: 1_760_086_400 },
  };
  return <TableScope scope={scope}>{table()}</TableScope>;
}

export function querySpy(): Mock<(next: TokenQuery) => void> {
  return vi.fn<(next: TokenQuery) => void>();
}

export function lastTables(
  spy: Mock<(next: TokenQuery) => void>,
): Record<string, string> {
  return spy.mock.lastCall?.[0].tables ?? {};
}
