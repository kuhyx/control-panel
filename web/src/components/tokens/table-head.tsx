import { type TableState, toggleSort } from "../../lib/table-parameters.ts";
import { type ColumnMeta, FilterCell } from "./table-filters.tsx";

export interface HeadColumn {
  key: string;
  label: string;
  num?: boolean;
}

function arrow(state: TableState, key: string): string {
  const index = state.sort.findIndex((s) => s.key === key);
  if (index === -1) return "";
  const glyph = state.sort[index]?.desc === true ? "▼" : "▲";
  return state.sort.length > 1 ? ` ${glyph}${String(index + 1)}` : ` ${glyph}`;
}

function ariaSort(
  state: TableState,
  key: string,
): "ascending" | "descending" | "none" {
  if (state.sort[0]?.key !== key) return "none";
  return state.sort[0].desc ? "descending" : "ascending";
}

// Sortable header row (click: sort by it; shift-click: add a secondary key)
// and a filter row underneath, one control per column.
export function TableHead({
  allSelected,
  columns,
  meta,
  onSelectAll,
  onState,
  state,
}: Readonly<{
  allSelected: boolean;
  columns: HeadColumn[];
  meta: Record<string, ColumnMeta>;
  onSelectAll: (isSelected: boolean) => void;
  onState: (next: TableState) => void;
  state: TableState;
}>): React.JSX.Element {
  return (
    <thead>
      <tr>
        <th>
          <input
            aria-label="select all rows"
            checked={allSelected}
            onChange={(event) => {
              onSelectAll(event.target.checked);
            }}
            type="checkbox"
          />
        </th>
        {columns.map((c) => {
          return (
            <th
              aria-sort={ariaSort(state, c.key)}
              className={c.num === true ? "num" : undefined}
              key={c.key}
            >
              <button
                className="sort-button"
                onClick={(event) => {
                  onState({
                    ...state,
                    sort: toggleSort(state.sort, c.key, event.shiftKey),
                  });
                }}
                title="click: sort; shift-click: add as next sort key"
                type="button"
              >
                {c.label}
                {arrow(state, c.key)}
              </button>
            </th>
          );
        })}
      </tr>
      <tr className="filter-row">
        <th />
        {columns.map((c) => {
          return (
            <th key={c.key}>
              <FilterCell
                label={c.label}
                meta={meta[c.key]}
                onRule={(rule) => {
                  const filters = Object.fromEntries(
                    Object.entries({ ...state.filters, [c.key]: rule }).filter(
                      ([, value]) => value !== "",
                    ),
                  );
                  onState({ ...state, filters });
                }}
                rule={state.filters[c.key] ?? ""}
              />
            </th>
          );
        })}
      </tr>
    </thead>
  );
}
