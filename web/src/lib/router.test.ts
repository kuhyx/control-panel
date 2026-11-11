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

describe("moved token routes", () => {
  const usage = { id: "", name: "usage" };

  it("sends every other token route to the usage redirect", () => {
    expect(parseHash("#/tokens")).toEqual(usage);
    expect(parseHash("#/tokens/s/abc-1")).toEqual(usage);
    expect(parseHash("#/tokens/p/carry?x=1")).toEqual(usage);
    expect(parseLocation("/tokens", "")).toEqual(usage);
    expect(parseLocation("/tokens", "#/s/x")).toEqual({ id: "x", name: "detail" });
  });

  it("ignores trailing slashes on the path and an empty hash", () => {
    expect(parseLocation("/tokens//", "#/")).toEqual(usage);
    expect(parseLocation("/tokens/", "#")).toEqual(usage);
    expect(parseLocation("/", "")).toEqual({ id: "", name: "overview" });
    expect(parseLocation("", "")).toEqual({ id: "", name: "overview" });
    expect(parseLocation("/other", "")).toEqual({ id: "", name: "overview" });
  });
});
