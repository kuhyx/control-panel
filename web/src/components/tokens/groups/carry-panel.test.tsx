import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { CarryPanelData } from "./carry-panel.tsx";
import type { ChunkRow } from "./chunk-table.tsx";

import { INDEX } from "../../../test/tokens-fixture.ts";
import { view } from "../panels/carry-view.tsx";

const ROW: ChunkRow = {
  carry_usd: 1.5,
  count: 3,
  create_usd: 0.25,
  detail: "",
  label: "git status",
  tokens: 900,
  total_usd: 1.75,
};

const DATA: CarryPanelData = {
  attachments: [],
  caption: "Carry cost = creation + carry.",
  context_reads: [
    { ...ROW, detail: "/h/.claude/rules/a.md", label: "Read:rules" },
  ],
  daily: [
    { context_usd: 0.5, day: "2026-10-01", results_usd: 2 },
    { context_usd: 0.25, day: "2026-10-02", results_usd: 1 },
  ],
  families: [{ ...ROW, carried_calls: 12.5 }],
  hooks: [
    { ...ROW, detail: "cd_chain.sh", label: "PreToolUse:Bash (context)" },
  ],
  images: [],
  mcp: [],
  pasted_images: [],
  rereads: [],
  skills: [],
  totals: { carry_total_usd: 3.75, spend_usd: 15 },
  web: [],
};

describe("CarryPanel", () => {
  it("shows the headline, the daily split and every attribution table", () => {
    render(view.render(DATA, { index: INDEX }));
    const tiles = within(screen.getByRole("list", { name: "Carry summary" }));
    expect(tiles.getByText("$3.75")).toBeInTheDocument();
    expect(tiles.getByText("25.0%")).toBeInTheDocument();
    expect(
      screen.getByRole("img", { name: "Carry cost per day" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Carry cost = creation + carry."),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "By Bash command family / tool" }),
    ).toBeInTheDocument();
    expect(screen.getByText("calls carried (avg)")).toBeInTheDocument();
    expect(screen.getByText("12.5")).toBeInTheDocument();
    expect(screen.getByText("cd_chain.sh")).toBeInTheDocument();
    expect(screen.getAllByText("—").length).toBeGreaterThan(0);
    expect(screen.getAllByText("No rows match.")).toHaveLength(7);
    expect(view.name).toBe("carry");
  });

  it("dashes the share when there was no spend", () => {
    render(
      view.render(
        { ...DATA, totals: { carry_total_usd: 0, spend_usd: 0 } },
        { index: INDEX },
      ),
    );
    const tiles = within(screen.getByRole("list", { name: "Carry summary" }));
    expect(tiles.getByText("—")).toBeInTheDocument();
  });
});
