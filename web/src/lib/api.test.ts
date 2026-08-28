import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, fetchLog, fetchStatus } from "./api.ts";

function respond(body: unknown, isOk = true, status = 200): Response {
  return {
    json: () => Promise.resolve(body),
    ok: isOk,
    status,
  } as unknown as Response;
}

describe("api client", () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
  });

  it("fetches the fleet status", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(respond({ host: "x" })));
    await expect(fetchStatus()).resolves.toEqual({ host: "x" });
  });

  it("encodes the log id and passes the line count", async () => {
    const spy = vi.fn().mockResolvedValue(respond({ id: "a/b" }));
    vi.stubGlobal("fetch", spy);
    await fetchLog("a/b", 50);
    expect(spy).toHaveBeenCalledWith("/api/logs/a%2Fb?lines=50", {});
  });

  it("passes an abort signal through when given one", async () => {
    const spy = vi.fn().mockResolvedValue(respond({}));
    vi.stubGlobal("fetch", spy);
    const controller = new AbortController();
    await fetchStatus(controller.signal);
    expect(spy).toHaveBeenCalledWith("/api/status", {
      signal: controller.signal,
    });
  });

  it("raises on a non-2xx response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(respond(null, false, 500)),
    );
    await expect(fetchStatus()).rejects.toThrow(ApiError);
  });

  it("raises on malformed JSON rather than yielding undefined", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        json: () => Promise.reject(new Error("bad")),
        ok: true,
        status: 200,
      }),
    );
    await expect(fetchStatus()).rejects.toThrow(/malformed JSON/);
  });
});
