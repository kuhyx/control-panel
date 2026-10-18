import { describe, expect, it } from "vitest";

import { CONTEXT } from "../test/tokens-fixture.ts";
import { optimisationPrompt, overLimit } from "./context-prompt.ts";

describe("optimisation prompt", () => {
  it("defaults to the files over a limit", () => {
    expect(overLimit(CONTEXT.files).map((f) => f.path)).toEqual([
      "/home/kuhy/.claude/CLAUDE.md",
    ]);
  });

  it("lists each file's numbers, limits and $/day, with the instruction", () => {
    const text = optimisationPrompt(CONTEXT.files, "wc -lc {paths}");
    expect(text).toContain(
      "Shrink these 2 Claude Code context files below their limits.",
    );
    expect(text).toContain(
      "| /home/kuhy/.claude/CLAUDE.md | 4000 | 300 | 1000 | 200 lines (hard: only 200 lines load); 250 lines (budget: 250-line cap) | $0.2500 |",
    );
    expect(text).toContain("| /srv/b/CLAUDE.md | gone | — | 0 | — | $0.0000 |");
    expect(text).toContain(
      "without dropping any rule's prohibition, command, path or memory entry",
    );
    expect(text).toContain(
      "wc -lc /home/kuhy/.claude/CLAUDE.md /srv/b/CLAUDE.md",
    );
    expect(text).toContain("Commit narrowly");
  });

  it("names the applicable limits of a file that breaks none", () => {
    const [first] = CONTEXT.files;
    if (first === undefined) throw new Error("fixture");
    const ok = { ...first, breaches: [], status: "ok" as const };
    expect(optimisationPrompt([ok], "x")).toContain("| 200 lines; 250 lines |");
  });
});
