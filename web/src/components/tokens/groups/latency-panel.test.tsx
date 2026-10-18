import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { LatencyData } from "./latency-panel.tsx";

import { INDEX } from "../../../test/tokens-fixture.ts";
import { view } from "../panels/latency-view.tsx";

const ROW = { calls: 3, p50: 2.9, p90: 9, p99: 30, total_s: 40 };

const DATA: LatencyData = {
  caption: "Model latency = time to the first record.",
  daily: [
    { ...ROW, day: "2026-10-01" },
    { ...ROW, day: "2026-10-02", p99: null },
  ],
  models: [{ ...ROW, model: "claude-sonnet-5-5" }],
  think: { p50: 64, p90: 620, prompts: 1729 },
  think_histogram: [
    { bucket: "<10s", prompts: 121 },
    { bucket: "1-5m", prompts: 616 },
  ],
  tools: [
    { calls: 2, name: "AskUserQuestion", p50: 36, p95: null, total_s: 72 },
  ],
};

describe("LatencyPanel", () => {
  it("shows think-time tiles, both charts and both tables", () => {
    render(view.render(DATA, { index: INDEX }));
    const tiles = within(screen.getByRole("list", { name: "Think time" }));
    expect(tiles.getByText("1m")).toBeInTheDocument();
    expect(tiles.getByText("10m")).toBeInTheDocument();
    expect(tiles.getByText("1,729")).toBeInTheDocument();
    expect(
      screen.getByRole("img", { name: "Model latency per day" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("img", { name: "Prompts per think time" }),
    ).toBeInTheDocument();
    expect(screen.getByText("claude-sonnet-5-5")).toBeInTheDocument();
    expect(screen.getByText("AskUserQuestion")).toBeInTheDocument();
    expect(screen.getByText("2.9s")).toBeInTheDocument();
    expect(view.name).toBe("latency");
    expect(view.order).toBe(78);
  });

  it("dashes think time with no prompts", () => {
    render(
      view.render(
        { ...DATA, think: { p50: null, p90: null, prompts: 0 } },
        { index: INDEX },
      ),
    );
    const tiles = within(screen.getByRole("list", { name: "Think time" }));
    expect(tiles.getAllByText("—")).toHaveLength(2);
  });
});
