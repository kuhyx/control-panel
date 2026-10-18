import type { Tables } from "../../../lib/tokens-types.ts";

import { formatDay } from "../../../lib/tokens-api.ts";
import { type ColumnSpec, DataTable } from "../data-table.tsx";

type RawRow = Record<string, null | number | string> & {
  key: string;
  ts: number;
};

export interface ExportPanelData {
  _tables?: Tables;
  calls: RawRow[];
  caption: string;
  marks: RawRow[];
  turns: RawRow[];
}

const TABLES = [
  { id: "turns", title: "API calls" },
  { id: "calls", title: "Tool calls" },
  {
    id: "marks",
    title: "Context marks (hooks, attachments, compactions, errors)",
  },
] as const;

function unitOf(key: string): string | undefined {
  if (key.endsWith("usd")) return "USD";
  if (key === "ts") return "unix s";
  return key.endsWith("_s") ? "s" : undefined;
}

function columns(rows: RawRow[]): ColumnSpec<RawRow>[] {
  const keys = [...new Set(rows.flatMap((row) => Object.keys(row)))];
  return keys.map((key) => {
    const unit = unitOf(key);
    const base: ColumnSpec<RawRow> = {
      key,
      label: key,
      num: typeof rows[0]?.[key] === "number",
    };
    const withUnit = unit === undefined ? base : { ...base, unit };
    return key === "ts"
      ? { ...withUnit, format: (row: RawRow) => formatDay(row.ts) }
      : withUnit;
  });
}

export function ExportPanel({
  data,
}: Readonly<{ data: ExportPanelData }>): React.JSX.Element {
  return (
    <section className="card" id="export">
      <h2>Raw rows (export)</h2>
      <p className="caption">{data.caption}</p>
      {TABLES.map((table) => {
        const rows = data[table.id];
        return (
          <DataTable<RawRow>
            columns={columns(rows)}
            id={table.id}
            key={table.id}
            meta={data._tables?.[table.id]}
            rowKey={(row, index) =>
              `${row.key}|${String(row.ts)}|${String(index)}`
            }
            rows={rows}
            title={table.title}
          />
        );
      })}
    </section>
  );
}
