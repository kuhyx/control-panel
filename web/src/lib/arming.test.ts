import { describe, expect, it } from "vitest";

import type { Arming } from "./types.ts";

import { levelTone, requiresAttention, severityRank, toneFor } from "./arming.ts";

describe("arming helpers", () => {
  it("gives every state a token colour, never a raw hex", () => {
    const states: Arming[] = [
      "ARMED",
      "BAD",
      "DEGRADED",
      "NOT_INSTALLED",
      "RETIRED",
      "UNARMED",
      "UNKNOWN",
    ];
    for (const state of states) {
      expect(toneFor(state)).toMatch(/^var\(--/);
    }
  });

  it("ranks worst first, mirroring the Python severity order", () => {
    expect(severityRank("BAD")).toBeLessThan(severityRank("UNARMED"));
    expect(severityRank("UNARMED")).toBeLessThan(severityRank("ARMED"));
  });

  it("treats retired as a decision, not a fault", () => {
    expect(requiresAttention("RETIRED")).toBe(false);
    expect(requiresAttention("ARMED")).toBe(false);
    expect(requiresAttention("UNARMED")).toBe(true);
    expect(requiresAttention("NOT_INSTALLED")).toBe(true);
  });

  it("maps each level to a semantic token", () => {
    expect(levelTone("danger")).toBe("var(--danger)");
    expect(levelTone("warn")).toBe("var(--warning)");
    expect(levelTone("info")).toBe("var(--accent)");
  });
});
