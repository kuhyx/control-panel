import type {
  ContextFileDetail,
  SessionDetail,
  TokensIndex,
} from "./tokens-types.ts";

import { getJson } from "./api.ts";

// What the filter bar edits; serialised into the query string the panels take.
export interface TokenQuery {
  cwd: string;
  from: string;
  model: string;
  scope: string;
  to: string;
  window: string;
}

export const EMPTY_QUERY: TokenQuery = {
  cwd: "",
  from: "",
  model: "",
  scope: "all",
  to: "",
  window: "",
};

// Alphabetical, matching the property order every TokenQuery is built in, so
// the query string reads the same as it would from Object.entries.
const QUERY_KEYS: readonly (keyof TokenQuery)[] = [
  "cwd",
  "from",
  "model",
  "scope",
  "to",
  "window",
];

export function toSearch(query: TokenQuery): string {
  const parameters = new URLSearchParams();
  for (const key of QUERY_KEYS) {
    const value = query[key];
    if (value !== "" && !(key === "scope" && value === "all")) {
      parameters.set(key, value);
    }
  }
  return parameters.toString();
}

export function fromSearch(search: string): TokenQuery {
  const parameters = new URLSearchParams(search);
  const read = (key: keyof TokenQuery): string =>
    parameters.get(key) ?? EMPTY_QUERY[key];
  return {
    cwd: read("cwd"),
    from: read("from"),
    model: read("model"),
    scope: read("scope"),
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
    `/api/tokens/panel/${encodeURIComponent(name)}?${toSearch(query)}`,
    signal,
  );
}

export function fetchSession(
  key: string,
  signal?: AbortSignal,
): Promise<SessionDetail> {
  return getJson<SessionDetail>(
    `/api/tokens/session/${encodeURIComponent(key)}`,
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
