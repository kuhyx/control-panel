import type {
  ContextFileDetail,
  SessionDetail,
  TokensIndex,
} from "./tokens-types.ts";

import { getJson } from "./api.ts";
import { panelParameters, type TableParameters } from "./table-parameters.ts";

// What the filter bar edits; serialised into the query string the panels take.
export interface TokenQuery {
  cwd: string;
  from: string;
  model: string;
  scope: string;
  // Every table's search / filter / sort / limit, keyed `t.<panel>/<table>.*`.
  tables: TableParameters;
  to: string;
  window: string;
}

export const EMPTY_QUERY: TokenQuery = {
  cwd: "",
  from: "",
  model: "",
  scope: "all",
  tables: {},
  to: "",
  window: "",
};

// Alphabetical, matching the property order every TokenQuery is built in, so
// the query string reads the same as it would from Object.entries.
const QUERY_KEYS: readonly Exclude<keyof TokenQuery, "tables">[] = [
  "cwd",
  "from",
  "model",
  "scope",
  "to",
  "window",
];

function globalParameters(query: TokenQuery): URLSearchParams {
  const parameters = new URLSearchParams();
  for (const key of QUERY_KEYS) {
    const value = query[key];
    if (value !== "" && !(key === "scope" && value === "all")) {
      parameters.set(key, value);
    }
  }
  return parameters;
}

function withTables(parameters: URLSearchParams, tables: TableParameters): string {
  const sorted = Object.entries(tables).toSorted(([a], [b]) => a.localeCompare(b));
  for (const [key, value] of sorted) {
    parameters.set(key, value);
  }
  return parameters.toString();
}

// The page's whole state (filters + every table), as the URL hash carries it.
export function toSearch(query: TokenQuery): string {
  return withTables(globalParameters(query), query.tables);
}

// What one panel's API call sends: the filters plus its own tables only.
export function panelSearch(query: TokenQuery, panel: string): string {
  return withTables(globalParameters(query), panelParameters(query.tables, panel));
}

export function fromSearch(search: string): TokenQuery {
  const parameters = new URLSearchParams(search);
  const read = (key: Exclude<keyof TokenQuery, "tables">): string =>
    parameters.get(key) ?? EMPTY_QUERY[key];
  const tables: TableParameters = {};
  for (const [key, value] of parameters) {
    if (key.startsWith("t.")) tables[key] = value;
  }
  return {
    cwd: read("cwd"),
    from: read("from"),
    model: read("model"),
    scope: read("scope"),
    tables,
    to: read("to"),
    window: read("window"),
  };
}

export function fetchTokensIndex(signal?: AbortSignal): Promise<TokensIndex> {
  return getJson<TokensIndex>("/api/tokens", signal);
}

export function fetchPanel<T>(
  name: string,
  query: TokenQuery,
  signal?: AbortSignal,
): Promise<T> {
  return getJson<T>(
    `/api/tokens/panel/${encodeURIComponent(name)}?${panelSearch(query, name)}`,
    signal,
  );
}

export function fetchSession(
  key: string,
  signal?: AbortSignal,
  query: TokenQuery = EMPTY_QUERY,
): Promise<SessionDetail> {
  const search = withTables(
    new URLSearchParams(),
    panelParameters(query.tables, "session"),
  );
  const suffix = search === "" ? "" : `?${search}`;
  return getJson<SessionDetail>(
    `/api/tokens/session/${encodeURIComponent(key)}${suffix}`,
    signal,
  );
}

export function fetchContextFile(
  path: string,
  signal?: AbortSignal,
): Promise<ContextFileDetail> {
  return getJson<ContextFileDetail>(
    `/api/tokens/context-file?path=${encodeURIComponent(path)}`,
    signal,
  );
}

const SECONDS_PER_MINUTE = 60;
const SECONDS_PER_HOUR = 3600;

export function formatUsd(value: null | number): string {
  if (value === null) return "—";
  return value >= 100 ? `$${value.toFixed(0)}` : `$${value.toFixed(2)}`;
}

export function formatShare(value: null | number): string {
  return value === null ? "—" : `${(value * 100).toFixed(1)}%`;
}

export function formatDuration(seconds: number): string {
  if (seconds < SECONDS_PER_MINUTE) return `${Math.round(seconds)}s`;
  if (seconds < SECONDS_PER_HOUR) {
    return `${Math.round(seconds / SECONDS_PER_MINUTE)}m`;
  }
  // Round once, on total minutes, so 59.6 minutes carries into the hour.
  const total = Math.round(seconds / SECONDS_PER_MINUTE);
  const hours = Math.floor(total / SECONDS_PER_MINUTE);
  const minutes = total % SECONDS_PER_MINUTE;
  return `${hours}h${String(minutes).padStart(2, "0")}`;
}

export function formatCount(value: number): string {
  return value.toLocaleString("en-US");
}

export function formatDay(epochSeconds: number): string {
  const when = new Date(epochSeconds * 1000);
  return when.toLocaleString("en-GB", {
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    month: "short",
  });
}
