import type { SessionColumn } from "../../lib/sessions-query.ts";
import type { SortState } from "../../lib/table-state.ts";
import type { Selection } from "./use-selection.ts";

const LABELS: readonly (readonly [SessionColumn, string])[] = [
  ["status", "Status"],
  ["age", "Age"],
  ["project", "Project"],
  ["title", "Title"],
  ["mark", "Mark"],
];

// Same markup (and table-controls.css styling) as ColumnHeader.
const INDICATOR = { asc: "▲", desc: "▼", none: "↕" } as const;
const ARIA_SORT = { asc: "ascending", desc: "descending", none: "none" } as const;

// Select-all checkbox, then one sort button per column: a click cycles
// ascending, descending, off (off = the server's order).
export function SessionsHead({
  allState,
  onSelectAll,
  onSort,
  sort,
}: Readonly<{
  allState: Selection["allState"];
  onSelectAll: (isOn: boolean) => void;
  onSort: (column: SessionColumn) => void;
  sort: null | SortState;
}>): React.JSX.Element {
  return (
    <thead>
      <tr>
        <th className="select-cell" scope="col">
          <input
            aria-label="Select all shown sessions"
            checked={allState === "all"}
            onChange={() => {
              onSelectAll(allState !== "all");
            }}
            // indeterminate is a DOM property with no React prop.
            ref={(element) => {
              if (element !== null) element.indeterminate = allState === "some";
            }}
            type="checkbox"
          />
        </th>
        {LABELS.map(([column, label]) => {
          const active = sort?.column === column ? sort.direction : "none";
          return (
            <th aria-sort={ARIA_SORT[active]} className="sortable" key={column} scope="col">
              <button
                className="sort-button"
                onClick={() => {
                  onSort(column);
                }}
                type="button"
              >
                {label}
                <span aria-hidden="true" className={`sort-indicator sort-${active}`}>
                  {INDICATOR[active]}
                </span>
              </button>
            </th>
          );
        })}
        <th scope="col">Actions</th>
      </tr>
    </thead>
  );
}
