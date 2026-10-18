// CSV export of any table the page shows: built client-side from the rows it
// already has, so it costs no extra endpoint.
function stringify(value: unknown): string {
  if (typeof value === "string") return value;
  const isScalar = typeof value === "number" || typeof value === "boolean";
  return isScalar ? String(value) : JSON.stringify(value);
}

function cell(value: unknown): string {
  if (value === null || value === undefined) return "";
  const text = stringify(value);
  return /[",\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}

export function toCsv<T extends object>(rows: T[], columns: (keyof T)[]): string {
  const header = columns.map((c) => cell(c)).join(",");
  const body = rows.map((row) => columns.map((c) => cell(row[c])).join(","));
  return [header, ...body].join("\n");
}

export function CsvButton<T extends object>({
  columns,
  name,
  rows,
}: Readonly<{ columns: (keyof T)[]; name: string; rows: T[] }>): React.JSX.Element {
  const href = `data:text/csv;charset=utf-8,${encodeURIComponent(toCsv(rows, columns))}`;
  return (
    <a className="csv-link" download={name} href={href}>
      CSV
    </a>
  );
}
