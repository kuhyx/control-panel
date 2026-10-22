import { type Mock, vi } from "vitest";

import type { SessionEntry, SessionsPayload } from "../lib/sessions-api.ts";
import type { MutationResult } from "../lib/types.ts";

// /api/sessions shaped like the backend's output: one row per status, already
// in server order (not-done first, then done/continuing), and both a
// tag-done and a manually-marked done row.
function entry(
  id: string,
  status: SessionEntry["status"],
  extra: Partial<SessionEntry> = {},
): SessionEntry {
  const cwd = `/home/kuhy/src/${id}`;
  return {
    cwd,
    done: false,
    id,
    last_assistant: `assistant says ${id}`,
    last_ts: "2026-10-22T08:00:00.000Z",
    last_user: `user asks ${id}`,
    manual_mark: null,
    project: id,
    resume_command: `cd '${cwd}' && claude --resume ${id}`,
    status,
    title: `title of ${id}`,
    ...extra,
  };
}

export const NOW_MS = Date.parse("2026-10-22T11:00:00.000Z");

export const SESSIONS: SessionsPayload = {
  scan_ms: 840.2,
  scanned: 1033,
  sessions: [
    entry("alpha", "needs_action", {
      last_assistant: "NEEDS ACTION: run **the thing**",
    }),
    entry("bravo", "question"),
    entry("charlie", "untagged", { title: "Fix the Router" }),
    entry("delta", "running", { cwd: "/srv/Delta-Box" }),
    entry("echo", "done", { done: true }),
    entry("foxtrot", "done", { done: true, manual_mark: "done" }),
    entry("golf", "continuing", { done: true }),
  ],
};

export const RESUMED: MutationResult = {
  argv: ["claude", "--resume", "alpha"],
  ok: true,
  refused: false,
  stderr: "",
  stdout: "",
  summary: "Resumed alpha in a new terminal.",
};

function respond(body: unknown, isOk = true): Response {
  return {
    json: () => Promise.resolve(body),
    ok: isOk,
    status: isOk ? 200 : 500,
  } as unknown as Response;
}

// Stub `fetch`: GET /api/sessions answers `payload` (500 when null), every
// POST /api/mutate/* answers `result`.
export function stubSessionsFetch(
  payload: null | SessionsPayload = SESSIONS,
  result: MutationResult = RESUMED,
): Mock<(path: string, init?: RequestInit) => Promise<Response>> {
  const spy = vi.fn((path: string, init?: RequestInit) => {
    const isMutation = path.startsWith("/api/mutate/") && init !== undefined;
    return Promise.resolve(
      isMutation ? respond(result) : respond(payload, payload !== null),
    );
  });
  vi.stubGlobal("fetch", spy);
  return spy;
}

// The JSON bodies POSTed to one mutation, in call order.
export function postedBodies(
  spy: Mock<(path: string, init?: RequestInit) => Promise<Response>>,
  name: string,
): unknown[] {
  return spy.mock.calls
    .filter(([path]) => path === `/api/mutate/${name}`)
    .map(([, init]) => JSON.parse(init?.body as string) as unknown);
}
