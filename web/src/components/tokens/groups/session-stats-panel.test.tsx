import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { SessionStatsData } from "./session-stats-panel.tsx";

import { INDEX } from "../../../test/tokens-fixture.ts";
import { view } from "../panels/session-stats-view.tsx";

const DATA: SessionStatsData = {
  caption: "A session = one main transcript.",
  cost_hist: [
    { bucket: "<$0.50", sessions: 4 },
    { bucket: "$0.50-1", sessions: 1 },
  ],
  daily: [
    { day: "2026-10-01", max_concurrent: 3, sessions: 5 },
    { day: "2026-10-02", max_concurrent: 1, sessions: 2 },
  ],
  interrupts_hist: [{ bucket: "0", sessions: 5 }],
  position: [
    { bucket: "1", calls: 12, mean_usd: 0.23 },
    { bucket: "2-5", calls: 0, mean_usd: null },
  ],
  prompts_hist: [{ bucket: "1", sessions: 5 }],
  totals: { interrupts: 6, sessions: 7, usd: 82.5, usd_per_session: 11.79 },
};

describe("SessionStatsPanel", () => {
  it("shows the tiles, every distribution and both tables", () => {
    render(view.render(DATA, { index: INDEX }));
    const tiles = within(
      screen.getByRole("list", { name: "Session stats summary" }),
    );
    expect(tiles.getByText("$11.79")).toBeInTheDocument();
    expect(tiles.getByText("sessions, $82.50")).toBeInTheDocument();
    expect(tiles.getByText("6")).toBeInTheDocument();
    for (const name of [
      "Sessions by cost",
      "Mean USD of the n-th call",
      "Sessions by prompt count",
      "Sessions by interruptions",
      "Sessions per day and peak concurrency",
    ]) {
      expect(screen.getByRole("img", { name })).toBeInTheDocument();
    }
    expect(
      screen.getByRole("heading", { name: "Cost by call position" }),
    ).toBeInTheDocument();
    expect(screen.getByText("$0.23")).toBeInTheDocument();
    expect(screen.getByText("—")).toBeInTheDocument();
    expect(view.name).toBe("session_stats");
  });
});
