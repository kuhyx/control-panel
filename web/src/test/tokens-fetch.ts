import { type Mock, vi } from "vitest";

import type {
  SessionDetail,
  SubagentRow,
  TokensIndex,
} from "../lib/tokens-types.ts";

import {
  AB,
  CONTEXT,
  EFFICIENCY,
  FILE,
  INDEX,
  LEVERS,
  OVERVIEW,
  SESSION_ROW,
  SESSIONS,
} from "./tokens-fixture.ts";

const SUBAGENT: SubagentRow = {
  active_s: 30,
  agent_type: "Explore",
  calls: 5,
  depth: 1,
  description: "look around",
  key: "agent-1",
  model: "claude-sonnet",
  usd: 0.4,
  wall_s: 45,
};

export const DETAIL: SessionDetail = {
  prompts: [
    {
      active_s: 120,
      calls: 9,
      idx: 0,
      subagents: [SUBAGENT, { ...SUBAGENT, depth: 3, key: "agent-2" }],
      text: "do the work",
      tools: [
        { calls: 3, carry_usd: 0.2, name: "Bash", result_tokens: 900, share: 0.6, usd: 1 },
        { calls: 1, carry_usd: 0, name: "(no tool)", result_tokens: 0, share: null, usd: 0.1 },
      ],
      ts: 1_760_000_000,
      usd: 3,
      usd_own: 2.6,
      usd_sub: 0.4,
      wall_s: 200,
    },
    { ...emptyPrompt(), idx: 1, text: "thanks" },
  ],
  session: SESSION_ROW,
  unattributed: [{ ...SUBAGENT, key: "orphan" }],
};

function emptyPrompt(): SessionDetail["prompts"][number] {
  return {
    active_s: 0,
    calls: 0,
    idx: 0,
    subagents: [],
    text: "",
    tools: [],
    ts: 1_760_000_000,
    usd: 0,
    usd_own: 0,
    usd_sub: 0,
    wall_s: 0,
  };
}

const PANELS: Record<string, unknown> = {
  ab: AB,
  context: CONTEXT,
  efficiency: EFFICIENCY,
  levers: LEVERS,
  overview: OVERVIEW,
  sessions: SESSIONS,
};

function respond(body: unknown, isOk = true): Response {
  return {
    json: () => Promise.resolve(body),
    ok: isOk,
    status: isOk ? 200 : 500,
  } as unknown as Response;
}

function route(path: string, index: TokensIndex): unknown {
  if (path === "/api/tokens") return index;
  if (path.startsWith("/api/tokens/session/")) return DETAIL;
  if (path.startsWith("/api/tokens/context-file")) return FILE;
  const name = /\/panel\/(\w+)/.exec(path)?.[1] ?? "";
  return PANELS[name];
}

// Stub `fetch` with every token endpoint; any path containing one of
// `failing` answers 500 instead.
export function stubTokensFetch(
  failing: string[] = [],
  index: TokensIndex = INDEX,
): Mock<(path: string) => Promise<Response>> {
  const spy = vi.fn((path: string) => {
    const isFailing = failing.some((part) => path.includes(part));
    const body = isFailing ? null : route(path, index);
    // A panel group without a fixture here stays "Reading…" (never answers),
    // so page tests need no edit for every new group.
    return body === undefined
      ? new Promise<Response>(() => null)
      : Promise.resolve(respond(body, !isFailing));
  });
  vi.stubGlobal("fetch", spy);
  return spy;
}

// A fetch that never answers but rejects once its request is aborted, to
// exercise the unmount-while-loading path.
export function stubHangingFetch(): void {
  vi.stubGlobal(
    "fetch",
    vi.fn((_path: string, init: RequestInit) => {
      return new Promise((_resolve, reject) => {
        init.signal?.addEventListener("abort", () => {
          reject(new Error("aborted"));
        });
      });
    }),
  );
}
