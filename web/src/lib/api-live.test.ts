import { beforeEach, describe, expect, it, vi } from "vitest";

import { fetchJournal, fetchUnknown, restart } from "./api.ts";

function respond(body: unknown): Response {
  return {
    json: () => Promise.resolve(body),
    ok: true,
    status: 200,
  } as unknown as Response;
}

describe("api client: the running half", () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
  });

  it("encodes the journal name and passes the line count", async () => {
    const spy = vi.fn().mockResolvedValue(respond({ lines: [] }));
    vi.stubGlobal("fetch", spy);
    await fetchJournal("user", "a@b.service", 100);
    expect(spy).toHaveBeenCalledWith(
      "/api/journal/user/a%40b.service?lines=100",
      {},
    );
  });

  it("fetches the undeclared report", async () => {
    const spy = vi.fn().mockResolvedValue(respond({ listeners: [], units: [] }));
    vi.stubGlobal("fetch", spy);
    await expect(fetchUnknown()).resolves.toEqual({ listeners: [], units: [] });
    expect(spy).toHaveBeenCalledWith("/api/unknown", {});
  });

  it("restarts through the JSON mutation endpoint", async () => {
    const spy = vi.fn().mockResolvedValue(respond({ ok: true }));
    vi.stubGlobal("fetch", spy);
    await restart("container", "gitea");
    // The server refuses any POST that is not application/json (CSRF guard).
    expect(spy).toHaveBeenCalledWith("/api/mutate/restart", {
      body: '{"kind":"container","name":"gitea"}',
      headers: { "Content-Type": "application/json" },
      method: "POST",
    });
  });
});
