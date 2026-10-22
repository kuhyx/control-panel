import { describe, expect, it } from "vitest";

import { parseHash, parseLocation } from "./router.ts";

describe("parseHash", () => {
  it("defaults to the overview", () => {
    expect(parseHash("")).toEqual({ id: "", name: "overview" });
    expect(parseHash("#/")).toEqual({ id: "", name: "overview" });
    expect(parseHash("#/nonsense")).toEqual({ id: "", name: "overview" });
  });

  it("routes to a subsystem", () => {
    expect(parseHash("#/s/hosts")).toEqual({ id: "hosts", name: "detail" });
  });

  it("routes to a log", () => {
    expect(parseHash("#/logs/hosts-monitor")).toEqual({
      id: "hosts-monitor",
      name: "logs",
    });
  });

  it("ignores a table-state query on every route", () => {
    expect(parseHash("#/s/hosts?units.sort=state:desc")).toEqual({
      id: "hosts",
      name: "detail",
    });
    expect(parseHash("#/logs/x?a=b")).toEqual({ id: "x", name: "logs" });
    expect(parseHash("#/?fleet.q.subsystem=a")).toEqual({ id: "", name: "overview" });
    expect(parseHash("#?fleet.sort=state:asc")).toEqual({ id: "", name: "overview" });
  });

  it("ignores a route with no id", () => {
    expect(parseHash("#/s/")).toEqual({ id: "", name: "overview" });
    expect(parseHash("#/logs")).toEqual({ id: "", name: "overview" });
  });
});

describe("token routes", () => {
  it("routes the tokens page by hash and by the /tokens path", () => {
    expect(parseHash("#/tokens")).toEqual({ id: "", name: "tokens" });
    expect(parseHash("#/tokens?from=2026-10-10")).toEqual({ id: "", name: "tokens" });
    expect(parseLocation("/tokens", "")).toEqual({ id: "", name: "tokens" });
    expect(parseLocation("/", "#/s/x")).toEqual({ id: "x", name: "detail" });
  });

  it("ignores trailing slashes on the path and an empty hash", () => {
    expect(parseLocation("/tokens//", "#/")).toEqual({ id: "", name: "tokens" });
    expect(parseLocation("/tokens/", "#")).toEqual({ id: "", name: "tokens" });
    expect(parseLocation("/", "")).toEqual({ id: "", name: "overview" });
    expect(parseLocation("", "")).toEqual({ id: "", name: "overview" });
    expect(parseLocation("/other", "")).toEqual({ id: "", name: "overview" });
  });

  it("routes one context file", () => {
    expect(parseHash(`#/tokens/f/${encodeURIComponent("/a/b.md")}`)).toEqual({
      id: "/a/b.md",
      name: "tokens-file",
    });
    expect(parseHash("#/tokens/x/y")).toEqual({ id: "", name: "tokens" });
    expect(parseHash("#/tokens/p/carry?t.carry%2Fmcp.limit=0")).toEqual({
      id: "carry",
      name: "tokens-panel",
    });
  });

  it("routes one session", () => {
    expect(parseHash("#/tokens/s/abc-1")).toEqual({
      id: "abc-1",
      name: "tokens-session",
    });
  });

  it("routes the sessions tab by hash and by path", () => {
    const sessions = { id: "", name: "tokens-sessions" };
    expect(parseHash("#/tokens/sessions")).toEqual(sessions);
    expect(parseHash("#/tokens/sessions/")).toEqual(sessions);
    expect(parseHash("#/tokens/sessions?done=1&q=x")).toEqual(sessions);
    expect(parseLocation("/tokens/sessions", "")).toEqual(sessions);
    expect(parseLocation("/tokens/sessions/", "#/")).toEqual(sessions);
    expect(parseLocation("/tokens/sessions", "#/tokens")).toEqual({
      id: "",
      name: "tokens",
    });
  });
});
