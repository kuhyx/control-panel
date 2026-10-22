import type { MutationResult } from "./types.ts";

import { getJson, mutate } from "./api.ts";

// One Claude Code session as /api/sessions reports it (see the backend's
// session scanner). `status` comes from the last reply's status tag;
// `done` folds in a manual mark, so it is what "Show done" hides.
export type SessionStatus =
  | "continuing"
  | "done"
  | "needs_action"
  | "question"
  | "running"
  | "untagged";

export interface SessionEntry {
  cwd: string;
  done: boolean;
  id: string;
  last_assistant: string;
  last_ts: string;
  last_user: string;
  manual_mark: "done" | null;
  project: string;
  resume_command: string;
  status: SessionStatus;
  title: string;
}

export interface SessionsPayload {
  scan_ms: number;
  scanned: number;
  // Already in display order: not-done first, newest first within a group.
  sessions: SessionEntry[];
}

// What the Sessions tab keeps in the hash query: `done=1&q=…`.
export interface SessionsQuery {
  q: string;
  showDone: boolean;
}

export function fetchSessions(signal?: AbortSignal): Promise<SessionsPayload> {
  return getJson<SessionsPayload>("/api/sessions", signal);
}

export function resumeSession(id: string): Promise<MutationResult> {
  return mutate("session-resume", { id });
}

export function markSession(
  id: string,
  mark: "done" | null,
): Promise<MutationResult> {
  return mutate("session-mark", { id, mark });
}

export function sessionsFromSearch(search: string): SessionsQuery {
  const parameters = new URLSearchParams(search);
  return {
    q: parameters.get("q") ?? "",
    showDone: parameters.get("done") === "1",
  };
}

export function sessionsToSearch(query: SessionsQuery): string {
  const parameters = new URLSearchParams();
  if (query.showDone) parameters.set("done", "1");
  if (query.q !== "") parameters.set("q", query.q);
  return parameters.toString();
}

// Filter only, never re-sort: the server's order is the point of the list.
export function visibleSessions(
  sessions: readonly SessionEntry[],
  query: SessionsQuery,
): SessionEntry[] {
  const needle = query.q.trim().toLowerCase();
  return sessions.filter((session) => {
    if (session.done && !query.showDone) return false;
    const haystack = `${session.project}\n${session.title}\n${session.cwd}`;
    return haystack.toLowerCase().includes(needle);
  });
}

// Header order, and how each status reads after its count.
const LABELS: readonly (readonly [SessionStatus, string, string])[] = [
  ["needs_action", "need action", "need action"],
  ["question", "question", "questions"],
  ["untagged", "untagged", "untagged"],
  ["running", "running", "running"],
  ["done", "done", "done"],
  ["continuing", "continuing", "continuing"],
];

// "3 need action · 2 questions · …" over every session, filter or not.
export function statusCounts(sessions: readonly SessionEntry[]): string {
  const parts: string[] = [];
  for (const [status, one, many] of LABELS) {
    const count = sessions.filter((s) => s.status === status).length;
    if (count > 0) parts.push(`${String(count)} ${count === 1 ? one : many}`);
  }
  return parts.length === 0 ? "no sessions" : parts.join(" · ");
}
