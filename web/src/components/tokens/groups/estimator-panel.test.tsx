import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { EstimatorPanelData } from "./estimator-panel.tsx";

import { INDEX } from "../../../test/tokens-fixture.ts";
import { view } from "../panels/estimator-view.tsx";

const DATA: EstimatorPanelData = {
  caption: "A miss is actual > 2x the estimate.",
  events: [
    {
      count: 2,
      day: "2026-09-28",
      example: "Implement y",
      kind: "split-ignored",
    },
  ],
  events_daily: [
    { count: 2, day: "2026-09-28" },
    { count: 1, day: "2026-09-29" },
  ],
  filtered_by: "gate-miss events: date range only",
  sessions: [
    {
      actual_calls: 1,
      cwd: "/home/tester/src/a",
      est_calls: 0,
      first_ts: 1_760_000_000,
      miss: "over",
      ratio: null,
      session_id: "s3",
      title: "",
      usd: 0.5,
    },
    {
      actual_calls: 30,
      cwd: "/home/tester",
      est_calls: 20,
      first_ts: 1_760_000_100,
      miss: "",
      ratio: 1.5,
      session_id: "s1",
      title: "fix a",
      usd: 6,
    },
  ],
  totals: {
    gate_misses: 3,
    median_ratio: 0.25,
    over_share: 0.5,
    predicted_fits: 1,
    sessions: 2,
    under_share: 0,
    within_share: 0.5,
  },
};

describe("EstimatorPanel", () => {
  it("shows hit-rate tiles, the gate-miss chart and both tables", () => {
    render(view.render(DATA, { index: INDEX }));
    const tiles = within(
      screen.getByRole("list", { name: "Estimator summary" }),
    );
    expect(tiles.getAllByText("50.0%")).toHaveLength(2);
    expect(tiles.getByText("0.25×")).toBeInTheDocument();
    expect(tiles.getByText("3")).toBeInTheDocument();
    expect(
      screen.getByRole("img", { name: "Context-gate misses per day" }),
    ).toBeInTheDocument();
    expect(screen.getByText(/date range only/u)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "fix a" })).toHaveAttribute(
      "href",
      "#/tokens/s/s1",
    );
    expect(screen.getByRole("link", { name: "s3" })).toBeInTheDocument();
    expect(screen.getByText("1.50×")).toBeInTheDocument();
    expect(screen.getByText("over")).toBeInTheDocument();
    expect(screen.getByText("Implement y")).toBeInTheDocument();
    expect(view.name).toBe("estimator");
    expect(view.order).toBe(84);
  });

  it("dashes the median when no session has a ratio", () => {
    render(
      view.render(
        { ...DATA, totals: { ...DATA.totals, median_ratio: null } },
        { index: INDEX },
      ),
    );
    const tiles = within(
      screen.getByRole("list", { name: "Estimator summary" }),
    );
    expect(tiles.getByText("—")).toBeInTheDocument();
  });
});
