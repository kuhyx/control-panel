import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { AnomaliesPanelData } from "./anomalies-panel.tsx";

import { INDEX } from "../../../test/tokens-fixture.ts";
import { view } from "../panels/anomalies-view.tsx";

const DATA: AnomaliesPanelData = {
  caption: "Spikes: days over 2x the median.",
  categories: [
    { calls: 4, category: "polling", cost_usd: 0.22, key: "s4" },
    { calls: 2, category: "lint-test", cost_usd: 0.62, key: "s4" },
  ],
  category_totals: [{ calls: 6, category: "lint-test", cost_usd: 0.84 }],
  expensive: [
    {
      calls: 2476,
      cwd: "/home/kuhy",
      day: "2026-09-21",
      key: "8e96",
      title: "/clear",
      usd: 572.39,
    },
  ],
  loops: [
    { cost_usd: 0.43, key: "aea0", name: "Read", repeats: 3, target: "/a.png" },
  ],
  over: 20,
  spikes: [{ day: "2026-10-09", median_usd: 56.87, ratio: 7.158, usd: 407.12 }],
};

describe("AnomaliesPanel", () => {
  it("shows the tiles and every anomaly table", () => {
    render(view.render(DATA, { index: INDEX }));
    const tiles = within(
      screen.getByRole("list", { name: "Anomalies summary" }),
    );
    expect(tiles.getByText("sessions over $20.00")).toBeInTheDocument();
    expect(tiles.getAllByText("1")).toHaveLength(3);
    expect(screen.getByText("7.2×")).toBeInTheDocument();
    expect(screen.getByText("$572")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Sessions over $20.00" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Polling / lint-test / VCS calls" }),
    ).toBeInTheDocument();
    expect(screen.getByText("$0.84")).toBeInTheDocument();
    expect(screen.getByText("/a.png")).toBeInTheDocument();
    expect(view.name).toBe("anomalies");
  });
});
