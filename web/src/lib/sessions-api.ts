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

export function fetchSessions(signal?: AbortSignal): Promise<SessionsPayload> {
  return getJson<SessionsPayload>("/api/sessions", signal);
}

export function deleteSession(id: string): Promise<MutationResult> {
  return mutate("session-delete", { id });
}

// One request for the whole selection (a single row sends [id]), one answer.
export function markSessions(
  ids: readonly string[],
  mark: "done" | null,
): Promise<MutationResult> {
  return mutate("session-mark", { ids, mark });
}

// The server opens one terminal per id and refuses more than five.
export function resumeSessions(ids: readonly string[]): Promise<MutationResult> {
  return mutate("session-resume", { ids });
}

// Transcripts move to ~/.claude/projects-trash/; a session active in the last
// ten minutes is refused rather than deleted from under its terminal.
export function deleteSessions(ids: readonly string[]): Promise<MutationResult> {
  return mutate("session-delete", { ids });
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

// The server's priority order, which the Status column sorts by.
export const STATUS_ORDER: readonly SessionStatus[] = LABELS.map(([status]) => status);

// "3 need action · 2 questions · …" over every session, filter or not.
export function statusCounts(sessions: readonly SessionEntry[]): string {
  const parts: string[] = [];
  for (const [status, one, many] of LABELS) {
    const count = sessions.filter((s) => s.status === status).length;
    if (count > 0) parts.push(`${String(count)} ${count === 1 ? one : many}`);
  }
  return parts.length === 0 ? "no sessions" : parts.join(" · ");
}
