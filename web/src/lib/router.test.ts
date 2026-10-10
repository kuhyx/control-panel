import { describe, expect, it } from "vitest";

import { parseHash } from "./router.ts";

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
