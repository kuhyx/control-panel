import { type Mock, vi } from "vitest";

import type { SessionEntry, SessionsPayload } from "../lib/sessions-api.ts";
import type { MutationResult } from "../lib/types.ts";

// /api/sessions shaped like the backend's output: one row per status, already
// in server order (not-done first, then done/continuing), and both a
// tag-done and a manually-marked done row. Ages (against NOW_MS) and projects
// vary so every sort and filter has something to reorder or drop:
//   alpha 3 h panel · bravo 30 min panel · charlie 2 d router · delta 10 min
//   · echo 9 d panel · foxtrot 3 w (by hand) · golf 1 h.
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
      project: "panel",
    }),
    entry("bravo", "question", {
      last_ts: "2026-10-22T10:30:00.000Z",
      project: "panel",
    }),
    entry("charlie", "untagged", {
      last_ts: "2026-10-20T11:00:00.000Z",
      project: "router",
      title: "Fix the Router",
    }),
    entry("delta", "running", {
      cwd: "/srv/Delta-Box",
      last_ts: "2026-10-22T10:50:00.000Z",
    }),
    entry("echo", "done", {
      done: true,
      last_ts: "2026-10-13T11:00:00.000Z",
      project: "panel",
    }),
    entry("foxtrot", "done", {
      done: true,
      last_ts: "2026-10-01T11:00:00.000Z",
      manual_mark: "done",
    }),
    entry("golf", "continuing", {
      done: true,
      last_ts: "2026-10-22T10:00:00.000Z",
    }),
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

function isList(
  payload: null | readonly SessionsPayload[] | SessionsPayload,
): payload is readonly SessionsPayload[] {
  return Array.isArray(payload);
}

export const REFUSED: MutationResult = {
  argv: [],
  ok: false,
  refused: true,
  stderr: "",
  stdout: "",
  summary: "Refused: bravo was active 2 minutes ago.",
};

// Stub `fetch`: GET /api/sessions answers `payload` (500 when null; a list is
// served in turn, its last entry repeating), every POST /api/mutate/*
// answers `result`.
export function stubSessionsFetch(
  payload: null | readonly SessionsPayload[] | SessionsPayload = SESSIONS,
  result: MutationResult = RESUMED,
): Mock<(path: string, init?: RequestInit) => Promise<Response>> {
  const queue = isList(payload) ? payload : [payload];
  let served = 0;
  const spy = vi.fn((path: string, init?: RequestInit) => {
    const isMutation = path.startsWith("/api/mutate/") && init !== undefined;
    if (isMutation) return Promise.resolve(respond(result));
    const next = queue[Math.min(served, queue.length - 1)] ?? null;
    served += 1;
    return Promise.resolve(respond(next, next !== null));
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
