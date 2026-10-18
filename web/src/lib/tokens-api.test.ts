import { beforeEach, describe, expect, it, vi } from "vitest";

import { stubTokensFetch } from "../test/tokens-fetch.ts";
import {
  EMPTY_QUERY,
  fetchContextFile,
  fetchPanel,
  fetchSession,
  fetchTokensIndex,
  formatCount,
  formatDay,
  formatDuration,
  formatShare,
  formatUsd,
  fromSearch,
  toSearch,
} from "./tokens-api.ts";

describe("token query string", () => {
  it("drops empty fields and the default scope", () => {
    expect(toSearch(EMPTY_QUERY)).toBe("");
    expect(toSearch({ ...EMPTY_QUERY, cwd: "/a b", from: "2026-10-01", scope: "sub" })).toBe(
      "cwd=%2Fa+b&from=2026-10-01&scope=sub",
    );
  });

  it("reads missing fields as their defaults", () => {
    expect(fromSearch("")).toEqual(EMPTY_QUERY);
    expect(fromSearch("model=opus&window=w1")).toEqual({
      ...EMPTY_QUERY,
      model: "opus",
      window: "w1",
    });
  });

  it("round-trips every field", () => {
    const query = {
      cwd: "/x",
      from: "2026-01-01",
      model: "m",
      scope: "main",
      to: "2026-02-01",
      window: "w",
    };
    expect(fromSearch(toSearch(query))).toEqual(query);
  });
});

describe("token fetchers", () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
  });

  it("builds every endpoint path", async () => {
    const spy = stubTokensFetch();
    const controller = new AbortController();
    await fetchTokensIndex(controller.signal);
    await fetchPanel("a/b", { ...EMPTY_QUERY, model: "m" });
    await fetchSession("s 1");
    await fetchContextFile("/a/b.md");
    expect(spy.mock.calls.map((call) => call[0])).toEqual([
      "/api/tokens",
      "/api/tokens/panel/a%2Fb?model=m",
      "/api/tokens/session/s%201",
      "/api/tokens/context-file?path=%2Fa%2Fb.md",
    ]);
  });
});

describe("token formatters", () => {
  it("formats USD with fewer decimals for large values", () => {
    expect(formatUsd(null)).toBe("—");
    expect(formatUsd(1.234)).toBe("$1.23");
    expect(formatUsd(123.4)).toBe("$123");
  });

  it("formats a share as a percentage", () => {
    expect(formatShare(null)).toBe("—");
    expect(formatShare(0.1234)).toBe("12.3%");
  });

  it("formats durations in seconds, minutes and hours", () => {
    expect(formatDuration(42.4)).toBe("42s");
    expect(formatDuration(150)).toBe("3m");
    expect(formatDuration(3600 * 2 + 5 * 60)).toBe("2h05");
    // 289h 59m 59s must carry into the hour, never render "289h60".
    expect(formatDuration(289 * 3600 + 59 * 60 + 59)).toBe("290h00");
  });

  it("formats counts and days", () => {
    expect(formatCount(1_234_567)).toBe("1,234,567");
    expect(formatDay(0)).toMatch(/Jan|Dec/);
  });
});
