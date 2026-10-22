import type { SortState } from "./table-state.ts";

import { type SessionEntry, type SessionStatus, STATUS_ORDER } from "./sessions-api.ts";

// What the Sessions tab keeps in the hash query, every key optional:
//   done=1  q=<text>  status=<s> (repeated)  project=<p>  older=<N><h|d|w>
//   mark=<manual|tag|open>  sort=<column>:<asc|desc>
// `done` and `q` lead, as they did before the other keys existed.

export type AgeUnit = "d" | "h" | "w";
// How a row stands: marked done by hand, done by its own status tag, or not
// done at all. "all" is no filter.
export type MarkFilter = "all" | RowMark;
export type RowMark = "manual" | "open" | "tag";
export type SessionColumn = "age" | "mark" | "project" | "status" | "title";

export interface SessionsQuery {
  // The age number as typed (so a half-typed value survives), and its unit.
  ageN: string;
  ageUnit: AgeUnit;
  mark: MarkFilter;
  project: string;
  q: string;
  showDone: boolean;
  sort: null | SortState;
  // Empty means every status.
  statuses: readonly SessionStatus[];
}

export const DEFAULT_QUERY: SessionsQuery = {
  ageN: "",
  ageUnit: "d",
  mark: "all",
  project: "",
  q: "",
  showDone: false,
  sort: null,
  statuses: [],
};

export const AGE_UNITS: readonly AgeUnit[] = ["h", "d", "w"];
const MARKS: readonly MarkFilter[] = ["all", "manual", "tag", "open"];
const UNIT_MS: Record<AgeUnit, number> = { d: 86_400_000, h: 3_600_000, w: 604_800_000 };
const AGE_NUMBER = /^\d+(?:\.\d+)?$/;
const OLDER = /^(\d+(?:\.\d+)?)([dhw])$/;
const MARK_RANK: Record<RowMark, number> = { manual: 0, open: 2, tag: 1 };

export function markOf(session: SessionEntry): RowMark {
  if (session.manual_mark === "done") return "manual";
  return session.done ? "tag" : "open";
}

const byText = (a: string, b: string): number =>
  a.localeCompare(b, undefined, { sensitivity: "base" });

// Ascending comparators. Age ascending is youngest first; status follows the
// server's priority order; mark puts by-hand, then by-tag, then not done.
const COMPARE: Record<SessionColumn, (a: SessionEntry, b: SessionEntry) => number> = {
  age: (a, b) => Date.parse(b.last_ts) - Date.parse(a.last_ts),
  mark: (a, b) => MARK_RANK[markOf(a)] - MARK_RANK[markOf(b)],
  project: (a, b) => byText(a.project, b.project),
  status: (a, b) => STATUS_ORDER.indexOf(a.status) - STATUS_ORDER.indexOf(b.status),
  title: (a, b) => byText(a.title, b.title),
};

const isColumn = (column: string): column is SessionColumn => Object.hasOwn(COMPARE, column);

function parseSort(raw: null | string): null | SortState {
  const [column = "", direction] = (raw ?? "").split(":", 2);
  if (!isColumn(column)) return null;
  return direction === "asc" || direction === "desc" ? { column, direction } : null;
}

export function sessionsFromSearch(search: string): SessionsQuery {
  const parameters = new URLSearchParams(search);
  const older = OLDER.exec(parameters.get("older") ?? "");
  const statuses = parameters.getAll("status");
  return {
    ageN: older?.[1] ?? "",
    ageUnit: AGE_UNITS.find((unit) => unit === older?.[2]) ?? "d",
    mark: MARKS.find((mark) => mark === parameters.get("mark")) ?? "all",
    project: parameters.get("project") ?? "",
    q: parameters.get("q") ?? "",
    showDone: parameters.get("done") === "1",
    sort: parseSort(parameters.get("sort")),
    statuses: STATUS_ORDER.filter((status) => statuses.includes(status)),
  };
}

// The age limit in ms, or null while the number box is empty or not a number.
function ageLimitMs(query: SessionsQuery): null | number {
  const typed = query.ageN.trim();
  return AGE_NUMBER.test(typed) ? Number(typed) * UNIT_MS[query.ageUnit] : null;
}

export function sessionsToSearch(query: SessionsQuery): string {
  const parameters = new URLSearchParams();
  if (query.showDone) parameters.set("done", "1");
  if (query.q !== "") parameters.set("q", query.q);
  for (const status of query.statuses) parameters.append("status", status);
  if (query.project !== "") parameters.set("project", query.project);
  if (ageLimitMs(query) !== null) {
    parameters.set("older", `${query.ageN.trim()}${query.ageUnit}`);
  }
  if (query.mark !== "all") parameters.set("mark", query.mark);
  if (query.sort !== null) {
    parameters.set("sort", `${query.sort.column}:${query.sort.direction}`);
  }
  return parameters.toString();
}

// "Show done" is one of three ways to ask for done rows, not a filter of its
// own. A done row (tag-done, continuing or marked by hand) shows when:
//   - Show done is ticked, or
//   - the Mark filter asks for done rows (by hand / by tag), or
//   - its own status (done or continuing) is ticked in the status chips.
// So ticking a done status or mark is enough to see those rows, and with
// Show done off a ticked "needs action" chip still hides a needs-action row
// that was marked done by hand. Every other filter then applies on top (AND).
function isDoneAllowed(session: SessionEntry, query: SessionsQuery): boolean {
  const isDoneStatus = session.status === "done" || session.status === "continuing";
  return (
    !session.done ||
    query.showDone ||
    query.mark === "manual" ||
    query.mark === "tag" ||
    (isDoneStatus && query.statuses.includes(session.status))
  );
}

// Filter only; the server's order stands until a column sort is picked.
export function filterSessions(
  sessions: readonly SessionEntry[],
  query: SessionsQuery,
  nowMs: number,
): SessionEntry[] {
  const needle = query.q.trim().toLowerCase();
  const limit = ageLimitMs(query);
  return sessions.filter((session) => {
    const haystack = `${session.project}\n${session.title}\n${session.cwd}`;
    return (
      isDoneAllowed(session, query) &&
      (query.statuses.length === 0 || query.statuses.includes(session.status)) &&
      (query.project === "" || session.project === query.project) &&
      (query.mark === "all" || markOf(session) === query.mark) &&
      (limit === null || nowMs - Date.parse(session.last_ts) > limit) &&
      haystack.toLowerCase().includes(needle)
    );
  });
}

// A stable sort, so ties keep the server's order in either direction.
export function sortSessions(
  sessions: readonly SessionEntry[],
  sort: null | SortState,
): SessionEntry[] {
  if (sort === null || !isColumn(sort.column)) return [...sessions];
  const compare = COMPARE[sort.column];
  const sign = sort.direction === "asc" ? 1 : -1;
  return sessions.toSorted((a, b) => sign * compare(a, b));
}

export function projectsOf(sessions: readonly SessionEntry[]): string[] {
  return [...new Set(sessions.map((s) => s.project))].toSorted(byText);
}
