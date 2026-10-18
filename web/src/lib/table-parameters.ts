// Table state <-> query parameters, in the grammar the backend's table layer
// (control_panel/tokens/_tables.py) applies, so the UI and any other client
// get identical rows for identical parameters:
//   t.<table>.q, t.<table>.f.<column>, t.<table>.sort, t.<table>.limit
// In the page's URL hash each table id is prefixed with its panel
// (`t.sessions/sessions.sort`), so one hash can hold every table's state and
// each panel only sends (and refetches on) its own.

export interface SortKey {
  desc: boolean;
  key: string;
}

export interface TableState {
  filters: Record<string, string>;
  limit: null | number;
  q: string;
  sort: SortKey[];
}

export type TableParameters = Record<string, string>;

export const EMPTY_TABLE: TableState = {
  filters: {},
  limit: null,
  q: "",
  sort: [],
};

export function decodeSort(text: string): SortKey[] {
  return text
    .split(",")
    .filter((part) => part.replace(/^-/, "") !== "")
    .map((part) => {
      return {
        desc: part.startsWith("-"),
        key: part.replace(/^-/, ""),
      };
    });
}

export function encodeSort(sort: SortKey[]): string {
  return sort.map((s) => `${s.desc ? "-" : ""}${s.key}`).join(",");
}

export function readTable(parameters: TableParameters, id: string): TableState {
  const prefix = `t.${id}.`;
  const filters: Record<string, string> = {};
  for (const [key, value] of Object.entries(parameters)) {
    if (key.startsWith(`${prefix}f.`))
      filters[key.slice(prefix.length + 2)] = value;
  }
  const limit = parameters[`${prefix}limit`];
  return {
    filters,
    limit: limit === undefined || !/^\d+$/.test(limit) ? null : Number(limit),
    q: parameters[`${prefix}q`] ?? "",
    sort: decodeSort(parameters[`${prefix}sort`] ?? ""),
  };
}

export function writeTable(
  parameters: TableParameters,
  id: string,
  state: TableState,
): TableParameters {
  const prefix = `t.${id}.`;
  const out: TableParameters = {};
  for (const [key, value] of Object.entries(parameters)) {
    if (!key.startsWith(prefix)) out[key] = value;
  }
  const put = (key: string, value: string): void => {
    if (value !== "") out[`${prefix}${key}`] = value;
  };
  put("q", state.q);
  put("sort", encodeSort(state.sort));
  put("limit", state.limit === null ? "" : String(state.limit));
  for (const [column, rule] of Object.entries(state.filters))
    put(`f.${column}`, rule);
  return out;
}

// The hash keys of one panel, re-keyed for that panel's API call.
export function panelParameters(parameters: TableParameters, panel: string): TableParameters {
  const prefix = `t.${panel}/`;
  const out: TableParameters = {};
  for (const [key, value] of Object.entries(parameters)) {
    if (key.startsWith(prefix)) out[`t.${key.slice(prefix.length)}`] = value;
  }
  return out;
}

// Click: sort by this column alone (toggling direction if it already leads).
// Shift-click: add it as the next key, or toggle it in place.
export function toggleSort(
  sort: SortKey[],
  key: string,
  isAppend: boolean,
): SortKey[] {
  const found = sort.find((s) => s.key === key);
  if (isAppend) {
    return found === undefined ? [...sort, { desc: true, key }] : sort.map((s) => (s.key === key ? { desc: !s.desc, key } : s));
  }
  const lead = sort[0];
  const isLeading = lead?.key === key;
  return [{ desc: !isLeading || !lead.desc, key }];
}

export function describeTable(state: TableState): string {
  const parts: string[] = [];
  if (state.q !== "") parts.push(`search "${state.q}"`);
  for (const [column, rule] of Object.entries(state.filters)) {
    parts.push(`${column} ${rule}`);
  }
  if (state.sort.length > 0) parts.push(`sort ${encodeSort(state.sort)}`);
  return parts.length === 0 ? "none" : parts.join(", ");
}
