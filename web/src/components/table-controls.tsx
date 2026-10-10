import type { ColumnSpec, TableView } from "../lib/table-state.ts";

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
        className="sort-button"
        onClick={() => {
          view.toggleSort(column.id);
        }}
        type="button"
      >
        {column.label}
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
          placeholder="search"
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
      <summary aria-label={`Filter ${column.label}`}>
        {selected.length === 0 ? "all" : `${String(selected.length)} selected`}
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
            <span>{value === "" ? "(empty)" : value}</span>
          </label>
          );
        })}
      </div>
    </details>
  );
}

/**
"N of M shown" plus a clear button; only present while something is filtering.
*/
export function TableHint<T>({ view }: Readonly<{ view: TableView<T> }>): null | React.JSX.Element {
  if (!view.filtered) return null;
  return (
    <p className="table-hint" role="status">
      {view.rows.length} of {view.total} shown
      <button className="link-button" onClick={view.clear} type="button">
        Clear filters
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
      <td className="empty" colSpan={colSpan}>
        No rows match the current filters.
      </td>
    </tr>
  );
}
