import { describe, expect, it } from "vitest";

import { formatBytes, formatEpochMicros, formatTimestamp } from "./format.ts";

describe("formatBytes", () => {
  it("renders a missing size as a dash", () => {
    expect(formatBytes(null)).toBe("—");
  });

  it("keeps bytes whole and scales larger units", () => {
    expect(formatBytes(512)).toBe("512 B");
    expect(formatBytes(1536)).toBe("1.5 KB");
    expect(formatBytes(57_282_668)).toBe("54.6 MB");
  });

  it("stops at the largest known unit", () => {
    expect(formatBytes(2 ** 60)).toContain("TB");
  });
});

describe("formatEpochMicros", () => {
  it("treats systemd timestamps as MICROseconds", () => {
    // Dividing by the wrong factor puts every "next run" in 1970.
    const rendered = formatEpochMicros("1787954400000000");
    expect(rendered).not.toContain("1970");
    expect(rendered).toContain("2026");
  });

  it("renders absent, zero and unparsable values as a dash", () => {
    expect(formatEpochMicros(null)).toBe("—");
    expect(formatEpochMicros("")).toBe("—");
    expect(formatEpochMicros("0")).toBe("—");
    expect(formatEpochMicros("not a number")).toBe("—");
  });
});

describe("formatTimestamp", () => {
  it("renders an ISO timestamp locally", () => {
    expect(formatTimestamp("2026-08-28T16:40:00+00:00")).toContain("2026");
  });

  it("passes an unparsable value straight through", () => {
    expect(formatTimestamp("whenever")).toBe("whenever");
  });
});
