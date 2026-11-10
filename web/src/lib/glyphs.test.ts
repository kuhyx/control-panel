import { describe, expect, it } from "vitest";

import { ARMING_GLYPH, armingGlyph, scopeGlyph, unitFileGlyph } from "./glyphs.ts";

describe("glyph lookups", () => {
  it("maps each known state to its own glyph", () => {
    expect(armingGlyph("ARMED")).toBe("✓");
    expect(armingGlyph("BAD")).toBe("✕");
    const distinct = new Set(Object.values(ARMING_GLYPH));
    expect(distinct.size).toBe(Object.keys(ARMING_GLYPH).length);
  });

  it("reads an unexpected state string as UNKNOWN", () => {
    expect(armingGlyph("SOMETHING_NEW")).toBe(ARMING_GLYPH.UNKNOWN);
  });

  it("maps scopes to shell prompts, a bullet for anything else", () => {
    expect(scopeGlyph("system")).toBe("#");
    expect(scopeGlyph("user")).toBe("$");
    expect(scopeGlyph("docker")).toBe("⬡");
    expect(scopeGlyph("session")).toBe("•");
  });

  it("maps unit-file states, a bullet for anything else", () => {
    expect(unitFileGlyph("enabled")).toBe("●");
    expect(unitFileGlyph("disabled")).toBe("○");
    expect(unitFileGlyph("transient")).toBe("•");
  });
});
