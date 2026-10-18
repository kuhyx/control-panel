import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { SpendMoreData } from "./spend-more-panel.tsx";

import { INDEX } from "../../../test/tokens-fixture.ts";
import { view } from "../panels/spend-more-view.tsx";
import { cellOpacity, Heatmap } from "./spend-more-heatmap.tsx";
import { monthSeries } from "./spend-more-panel.tsx";

const DATA: SpendMoreData = {
  block_daily: [{ blocks: 2, day: "2026-09-28", max_block_usd: 6 }],
  blocks: [
    {
      calls: 3,
      day: "2026-09-28",
      end: 1_790_000_000 + 18_000,
      first_ts: 1_790_000_000,
      last_ts: 1_790_003_600,
      start: 1_790_000_000,
      usd: 6,
      usd_per_hour: 6,
    },
  ],
  by_cwd: [
    { calls: 3, cwd: "/home/tester/src/a", share: 0.6, usd: 6.5 },
    { calls: 1, cwd: "/", share: 0.4, usd: 4 },
  ],
  by_model: [{ calls: 4, model: "claude-opus-5-5", share: 1, usd: 10.5 }],
  caption: "Spend = the API-call cost.",
  cumulative: [
    { cum_usd: 5, dom: 19, month: "2026-08", usd: 5 },
    { cum_usd: 6.5, dom: 28, month: "2026-09", usd: 6.5 },
    { cum_usd: 10.5, dom: 29, month: "2026-09", usd: 4 },
  ],
  grid: Array.from({ length: 7 }, (_, day) =>
    Array.from({ length: 24 }, (_, hour) => (day === 0 && hour === 14 ? 5 : 0)),
  ),
  heatmap: [{ calls: 2, hour: 14, usd: 5, weekday: 0 }],
  months: [
    { calls: 4, month: "2026-09", usd: 10.5 },
    { calls: 1, month: "2026-08", usd: 5 },
  ],
  rate_limits: [{ day: "2026-09-28", errors: 3 }],
  totals: { blocks: 3, peak_block_usd: 6, rate_limit_errors: 3, usd: 15.5 },
};

describe("SpendMorePanel", () => {
  it("shows the tiles, every chart, the heatmap and the tables", () => {
    render(view.render(DATA, { index: INDEX }));
    const tiles = within(
      screen.getByRole("list", { name: "Spend breakdown summary" }),
    );
    expect(tiles.getByText("$15.50")).toBeInTheDocument();
    expect(tiles.getByText("$6.00")).toBeInTheDocument();
    expect(tiles.getByText("costliest of 3 5-hour blocks")).toBeInTheDocument();
    for (const name of [
      "Cumulative spend within each month",
      "Spend per month",
      "Spend by model",
      "Spend by repo / cwd",
      "Spend by weekday and hour",
      "Costliest 5-hour block per day",
      "Rate-limit errors per day",
    ]) {
      expect(screen.getByRole("img", { name })).toBeInTheDocument();
    }
    expect(screen.getByText("Mon 14:00 — $5.00")).toBeInTheDocument();
    expect(screen.getAllByText("Mon")).toHaveLength(2);
    expect(
      screen.getByRole("heading", { name: "5-hour blocks" }),
    ).toBeInTheDocument();
    expect(view.name).toBe("spend_more");
  });

  it("splits the cumulative line into one series per month", () => {
    const series = monthSeries(DATA.cumulative);
    expect(series.map((s) => s.label)).toEqual(["2026-08", "2026-09"]);
    expect(series[1]?.points).toEqual([
      { x: "28", y: 6.5 },
      { x: "29", y: 10.5 },
    ]);
  });

  it("fades empty cells and scales the rest", () => {
    expect(cellOpacity(0, 5)).toBeCloseTo(0.04);
    expect(cellOpacity(5, 0)).toBeCloseTo(0.04);
    expect(cellOpacity(5, 5)).toBeCloseTo(1);
  });

  it("draws an empty grid as faint cells", () => {
    render(<Heatmap grid={[]} />);
    expect(screen.getByText("Sun 23:00 — $0.00")).toBeInTheDocument();
  });
});
