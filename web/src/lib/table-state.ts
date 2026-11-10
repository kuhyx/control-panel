import { useSyncExternalStore } from "react";

import { applyTableState, filterOptions, nextSort } from "./table-query.ts";

// Sort / filter / search state for a table, kept in the URL hash so it
// survives the auto-refresh (which re-renders everything) and a page reload.
//
// Format -- appended to the route as a query, every key namespaced by table so
// the unit table and container table on one detail page do not collide:
//   #/s/hosts?units.sort=state:desc&units.q.unit=foo&units.f.state=BAD&units.f.state=UNARMED
//   sort    <ns>.sort=<column>:<asc|desc>
//   search  <ns>.q.<column>=<text>
//   filter  <ns>.f.<column>=<value>   (repeated, one per selected value)
// Repeated keys rather than a comma list: a "Why" value is prose and may
// contain any separator.

export type SortDirection = "asc" | "desc";

export interface SortState {
  column: string;
  direction: SortDirection;
}

export interface TableState {
  filters: Readonly<Record<string, readonly string[]>>;
  search: Readonly<Record<string, string>>;
  sort: null | SortState;
}

export type SortKey = null | number | string;

export interface ColumnSpec<T> {
  /**
  Multi-select over the distinct values of `text`.
  */
  filter?: boolean;
  /**
  What the header paints; `label` is its spoken name only.
  */
  glyph: string;
  /**
  Stable, URL-safe id (no dots or colons).
  */
  id: string;
  label: string;
  /**
  Paints a filter option (an enum word) as a glyph; the value is spoken.
  */
  optionGlyph?: (value: string) => string;
  /**
  Case-insensitive free-text box over `text`.
  */
  search?: boolean;
  /**
  Defaults to `text`. Null always sorts last, whichever the direction.
  */
  sortKey?: (row: T) => SortKey;
  text: (row: T) => string;
}

export interface TableView<T> {
  clear: () => void;
  columns: readonly ColumnSpec<T>[];
  /**
  True when any search or filter narrows the rows.
  */
  filtered: boolean;
  ns: string;
  options: (column: ColumnSpec<T>) => string[];
  rows: T[];
  setFilter: (column: string, values: readonly string[]) => void;
  setSearch: (column: string, text: string) => void;
  state: TableState;
  toggleSort: (column: string) => void;
  total: number;
}

export const EMPTY_STATE: TableState = { filters: {}, search: {}, sort: null };

const CHANGE_EVENT = "table-state-change";
const SORT_SEPARATOR = ":";

function splitHash(hash: string): { path: string; query: string } {
  const clean = hash.replace(/^#/, "");
  const at = clean.indexOf("?");
  return at === -1
    ? { path: clean, query: "" }
    : { path: clean.slice(0, at), query: clean.slice(at + 1) };
}

export function readTableState(
  hash: string,
  ns: string,
  columnIds: readonly string[],
): TableState {
  const parameters = new URLSearchParams(splitHash(hash).query);
  const known = new Set(columnIds);
  const sortRaw = parameters.get(`${ns}.sort`) ?? "";
  const cut = sortRaw.lastIndexOf(SORT_SEPARATOR);
  const column = sortRaw.slice(0, cut);
  const direction = sortRaw.slice(cut + 1);
  const sort: null | SortState =
    cut > 0 && known.has(column) && (direction === "asc" || direction === "desc")
      ? { column, direction }
      : null;
  const search: Record<string, string> = {};
  const filters: Record<string, string[]> = {};
  for (const id of known) {
    const text = parameters.get(`${ns}.q.${id}`) ?? "";
    if (text !== "") search[id] = text;
    const values = parameters.getAll(`${ns}.f.${id}`);
    if (values.length > 0) filters[id] = values;
  }
  return { filters, search, sort };
}

// ":" stays literal so the hash reads `state:desc`, not `state%3Adesc`.
function encode(value: string): string {
  return encodeURIComponent(value).replaceAll("%3A", ":");
}

/**
Replace table `ns`'s params in `hash`, leaving the path and other tables alone.
*/
export function writeTableState(hash: string, ns: string, state: TableState): string {
  const { path, query } = splitHash(hash);
  const kept = query
    .split("&")
    .filter((part) => part !== "" && !part.startsWith(`${ns}.`));
  if (state.sort !== null) {
    kept.push(`${ns}.sort=${state.sort.column}${SORT_SEPARATOR}${state.sort.direction}`);
  }
  for (const [id, text] of Object.entries(state.search)) {
    if (text !== "") kept.push(`${ns}.q.${id}=${encode(text)}`);
  }
  for (const [id, values] of Object.entries(state.filters)) {
    for (const value of values) kept.push(`${ns}.f.${id}=${encode(value)}`);
  }
  return kept.length === 0 ? `#${path}` : `#${path}?${kept.join("&")}`;
}

function subscribe(listener: () => void): () => void {
  globalThis.addEventListener("hashchange", listener);
  globalThis.addEventListener(CHANGE_EVENT, listener);
  return () => {
    globalThis.removeEventListener("hashchange", listener);
    globalThis.removeEventListener(CHANGE_EVENT, listener);
  };
}

const currentHash = (): string => globalThis.location.hash;
const serverHash = (): string => "";

export function useTableView<T>(
  ns: string,
  columns: readonly ColumnSpec<T>[],
  rows: readonly T[],
): TableView<T> {
  const hash = useSyncExternalStore(subscribe, currentHash, serverHash);
  const ids = columns.map((column) => column.id);
  const state = readTableState(hash, ns, ids);

  // replaceState, not assigning location.hash: typing in a search box must not
  // add a history entry per keystroke. It fires no hashchange, so notify
  // ourselves. Read-modify-write against the live hash, not a stale closure.
  const update = (change: (current: TableState) => TableState): void => {
    const current = readTableState(globalThis.location.hash, ns, ids);
    const next = writeTableState(globalThis.location.hash, ns, change(current));
    globalThis.history.replaceState(globalThis.history.state, "", next);
    globalThis.dispatchEvent(new Event(CHANGE_EVENT));
  };

  const isFiltered =
    Object.keys(state.search).length > 0 || Object.keys(state.filters).length > 0;
  return {
    clear: () => {
      update((current) => ({ ...EMPTY_STATE, sort: current.sort }));
    },
    columns,
    filtered: isFiltered,
    ns,
    options: (column) => filterOptions(rows, column, state.filters[column.id] ?? []),
    rows: applyTableState(rows, columns, state),
    setFilter: (column, values) => {
      update((current) => {
        return {
          ...current,
          filters: { ...current.filters, [column]: values },
        };
      });
    },
    setSearch: (column, text) => {
      update((current) => {
        return {
          ...current,
          search: { ...current.search, [column]: text },
        };
      });
    },
    state,
    toggleSort: (column) => {
      update((current) => ({ ...current, sort: nextSort(current.sort, column) }));
    },
    total: rows.length,
  };
}
