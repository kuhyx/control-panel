import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { ToolRow, ToolsPanelData } from "./tools-panel.tsx";

import { INDEX } from "../../../test/tokens-fixture.ts";
import { view } from "../panels/tools-view.tsx";

const STATS: Omit<ToolRow, "name"> = {
  calls: 1200,
  denied: 2,
  error_rate: 0.05,
  errors: 60,
  hook: 3,
  rejected: 1,
  result_p50: 150,
  result_p95: null,
  time_cap: 0,
};

const DATA: ToolsPanelData = {
  batching: [
    { batched: 1, calls: 4, day: "2026-10-01", share: 0.25 },
    { batched: 0, calls: 0, day: "2026-10-02", share: null },
  ],
  caption: "Error rate = errors / calls.",
  families: [{ ...STATS, family: "git status" }],
  loops: [
    {
      cost_usd: 0.73,
      key: "s1",
      name: "Bash",
      repeats: 3,
      target: "git status",
    },
  ],
  time_cap: [{ count: 2, day: "2026-10-01", kind: "killed_foreground" }],
  tools: [{ ...STATS, name: "Bash" }],
  totals: {
    batched_share: 0.215,
    calls: 1200,
    error_rate: 0.05,
    errors: 60,
    failed: { denied: 2, hook: 3, rejected: 1 },
    time_cap_calls: 0,
    time_cap_events: { denied: 1, killed: 39, unmatched: 4 },
  },
};

describe("ToolsPanel", () => {
  it("shows the tiles, the batching chart and every table", () => {
    render(view.render(DATA, { index: INDEX }));
    const tiles = within(screen.getByRole("list", { name: "Tools summary" }));
    expect(tiles.getAllByText("1,200")).toHaveLength(1);
    expect(tiles.getByText("21.5%")).toBeInTheDocument();
    expect(tiles.getByText("6")).toBeInTheDocument();
    expect(tiles.getByText("39")).toBeInTheDocument();
    expect(
      screen.getByRole("img", { name: "Share of calls batched per day" }),
    ).toBeInTheDocument();
    for (const title of [
      "By tool",
      "By family",
      "Repeated identical calls (loops)",
      "Time-cap log by day",
      "Batching per day",
    ]) {
      expect(screen.getByRole("heading", { name: title })).toBeInTheDocument();
    }
    expect(screen.getByText("killed_foreground")).toBeInTheDocument();
    expect(screen.getByText("$0.73")).toBeInTheDocument();
    expect(screen.getAllByText("—").length).toBeGreaterThan(1);
    expect(view.name).toBe("tools");
  });

  it("dashes the time-cap kills when the log cannot be filtered", () => {
    render(
      view.render(
        { ...DATA, totals: { ...DATA.totals, time_cap_events: null } },
        { index: INDEX },
      ),
    );
    const tiles = within(screen.getByRole("list", { name: "Tools summary" }));
    expect(tiles.getByText("—")).toBeInTheDocument();
  });
});
