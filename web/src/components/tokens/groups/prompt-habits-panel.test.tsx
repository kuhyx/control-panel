import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { PromptHabitsData } from "./prompt-habits-panel.tsx";

import { INDEX } from "../../../test/tokens-fixture.ts";
import { view } from "../panels/prompt-habits-view.tsx";

const DATA: PromptHabitsData = {
  caption: "Length = characters of the opening prompt.",
  home: { session_share: 0.25, sessions: 3, usd: 40, usd_share: 0.4 },
  length_buckets: [
    { bucket: "no prompt", mean_usd: null, sessions: 0, total_usd: 0 },
    { bucket: "1-20", mean_usd: 19.34, sessions: 2, total_usd: 38.68 },
  ],
  prefixes: [
    { prefix: "LONG:", prompts: 14, session_usd: 638.37, sessions: 10 },
  ],
  sessions: [{ key: "s1", length: 17, prompt: "LONG: fix a thing", usd: 6 }],
};

describe("PromptHabitsPanel", () => {
  it("shows the home share, the length chart and the tables", () => {
    render(view.render(DATA, { index: INDEX }));
    const tiles = within(
      screen.getByRole("list", { name: "Prompt habits summary" }),
    );
    expect(tiles.getByText("40.0%")).toBeInTheDocument();
    expect(tiles.getByText("3")).toBeInTheDocument();
    expect(
      screen.getByRole("img", {
        name: "Mean session cost by opening prompt length",
      }),
    ).toBeInTheDocument();
    expect(screen.getByText("LONG: fix a thing")).toBeInTheDocument();
    expect(screen.getByText("$638")).toBeInTheDocument();
    expect(screen.getByText("$19.34")).toBeInTheDocument();
    expect(view.name).toBe("prompt_habits");
  });
});
