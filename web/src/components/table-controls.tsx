import type { ColumnSpec, TableView } from "../lib/table-state.ts";

import { GLYPH } from "../lib/glyphs.ts";
import { Glyph } from "./glyph.tsx";

// Header cell with the sort button and, per the column spec, a search box or a
// multi-select filter. A column with no spec (Actions) keeps a plain <th>.

const INDICATOR = { asc: "▲", desc: "▼", none: "↕" } as const;
const ARIA_SORT = { asc: "ascending", desc: "descending", none: "none" } as const;

export function ColumnHeader<T>({
  column,
  view,
}: Readonly<{
  column: ColumnSpec<T>;
  view: TableView<T>;
}>): React.JSX.Element {
  const active = view.state.sort?.column === column.id ? view.state.sort.direction : "none";
  return (
    <th aria-sort={ARIA_SORT[active]} className="sortable" scope="col">
      <button
        aria-label={column.label}
        className="sort-button"
        onClick={() => {
          view.toggleSort(column.id);
        }}
        type="button"
      >
        <span aria-hidden="true">{column.glyph}</span>
        <span aria-hidden="true" className={`sort-indicator sort-${active}`}>
          {INDICATOR[active]}
        </span>
      </button>
      {column.search === true && (
        <input
          aria-label={`Search ${column.label}`}
          className="column-search"
          onChange={(event) => {
            view.setSearch(column.id, event.target.value);
          }}
          type="search"
          value={view.state.search[column.id] ?? ""}
        />
      )}
      {column.filter === true && <FilterMenu column={column} view={view} />}
    </th>
  );
}

function FilterMenu<T>({
  column,
  view,
}: Readonly<{
  column: ColumnSpec<T>;
  view: TableView<T>;
}>): React.JSX.Element {
  const selected = view.state.filters[column.id] ?? [];
  const toggle = (value: string, isOn: boolean): void => {
    view.setFilter(
      column.id,
      isOn ? [...selected, value] : selected.filter((entry) => entry !== value),
    );
  };
  return (
    <details className="column-filter">
      {/* ▾ alone = no filter; a count = that many values picked. */}
      <summary aria-label={`Filter ${column.label}`}>
        {selected.length === 0 ? "▾" : `▾ ${String(selected.length)}`}
      </summary>
      <div aria-label={`${column.label} values`} className="filter-menu" role="group">
        {view.options(column).map((value) => {
          return (
          <label key={value}>
            <input
              checked={selected.includes(value)}
              onChange={(event) => {
                toggle(value, event.target.checked);
              }}
              type="checkbox"
            />
            <OptionLabel column={column} value={value} />
          </label>
          );
        })}
      </div>
    </details>
  );
}

function OptionLabel<T>({
  column,
  value,
}: Readonly<{ column: ColumnSpec<T>; value: string }>): React.JSX.Element {
  if (value === "") return <span aria-label="(empty)">—</span>;
  if (column.optionGlyph === undefined) return <span>{value}</span>;
  return <Glyph glyph={column.optionGlyph(value)} label={value} />;
}

/**
"N/M" plus a clear button; only present while something is filtering.
*/
export function TableHint<T>({ view }: Readonly<{ view: TableView<T> }>): null | React.JSX.Element {
  if (!view.filtered) return null;
  return (
    <p
      aria-label={`${String(view.rows.length)} of ${String(view.total)} shown`}
      className="table-hint"
      role="status"
    >
      {view.rows.length}/{view.total}
      <button
        aria-label="Clear filters"
        className="link-button"
        onClick={view.clear}
        type="button"
      >
        {GLYPH.clear}
      </button>
    </p>
  );
}

/**
Body row shown when every row is filtered out.
*/
export function NoMatchRow({ colSpan }: Readonly<{ colSpan: number }>): React.JSX.Element {
  return (
    <tr>
      <td aria-label="No rows match the current filters." className="empty" colSpan={colSpan}>
        {GLYPH.none}
      </td>
    </tr>
  );
}
