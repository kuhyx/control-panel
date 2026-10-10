import type {
  ColumnSpec,
  SortDirection,
  SortKey,
  SortState,
  TableState,
} from "./table-state.ts";

// The pure half of table-state: filtering, ordering and the sort cycle. Split
// out of table-state.ts (hash + hook) to stay under the file-length cap.

function compareKeys(a: SortKey, b: SortKey, direction: SortDirection): number {
  if (a === null || b === null) {
    if (a === b) return 0;
    return a === null ? 1 : -1; // nulls last in both directions
  }
  const flip = direction === "asc" ? 1 : -1;
  return ((typeof a === "number" && typeof b === "number" ? (a - b) : String(a).localeCompare(String(b), undefined, { numeric: true }))) * flip;
}

function sortKeyOf<T>(column: ColumnSpec<T>, row: T): SortKey {
  return column.sortKey === undefined ? column.text(row) : column.sortKey(row);
}

export function applyTableState<T>(
  rows: readonly T[],
  columns: readonly ColumnSpec<T>[],
  state: TableState,
): T[] {
  const kept = rows.filter((row) => {
    return columns.every((column) => {
      const needle = (state.search[column.id] ?? "").trim().toLowerCase();
      const chosen = state.filters[column.id] ?? [];
      const text = column.text(row);
      return (
        (needle === "" || text.toLowerCase().includes(needle)) &&
        (chosen.length === 0 || chosen.includes(text))
      );
    });
  },
  );
  const sorted = columns.find((column) => column.id === state.sort?.column);
  if (sorted === undefined || state.sort === null) return kept;
  const { direction } = state.sort;
  // toSorted is stable, so ties keep the caller's (declared) order.
  return kept.toSorted((a, b) =>
    compareKeys(sortKeyOf(sorted, a), sortKeyOf(sorted, b), direction),
  );
}

/**
Distinct values of a column, in its sort order; selected values are kept even if gone.
*/
export function filterOptions<T>(
  rows: readonly T[],
  column: ColumnSpec<T>,
  selected: readonly string[],
): string[] {
  const keys = new Map<string, SortKey>();
  for (const row of rows) keys.set(column.text(row), sortKeyOf(column, row));
  for (const value of selected) {
    if (!keys.has(value)) keys.set(value, value);
  }
  return [...keys]
    .toSorted(([, a], [, b]) => compareKeys(a, b, "asc"))
    .map(([value]) => value);
}

/**
Off -> ascending -> descending -> off.
*/
export function nextSort(current: null | SortState, column: string): null | SortState {
  if (current?.column !== column) return { column, direction: "asc" };
  return current.direction === "asc" ? { column, direction: "desc" } : null;
}
