import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { TokenClassesData } from "./token-classes-panel.tsx";

import { INDEX } from "../../../test/tokens-fixture.ts";
import { view } from "../panels/token-classes-view.tsx";

const DAY = {
  cache_read: 1000,
  cache_read_usd: 0.2,
  cold_starts: 1,
  cw_1h: 300,
  cw_1h_usd: 0.5,
  cw_5m: 200,
  cw_5m_usd: 0.25,
  day: "2026-10-01",
  hit_ratio: 0.5,
  input: 10,
  input_usd: 0.01,
  output: 50,
  output_usd: 1,
  spend_usd: 2,
  unsplit: 0,
  unsplit_usd: 0,
  usd: 1.96,
  waste_usd: 0.1,
};

const DATA: TokenClassesData = {
  caption: "Waste = no call within 1 h.",
  compactions: [
    {
      count: 2,
      duration_s: 31,
      est_usd: 0.42,
      key: "s1",
      model: "claude-opus-5-5",
      post_tokens: 20_000,
      pre_tokens: 160_000,
      trigger: "auto",
      ts: 1_790_000_000,
    },
  ],
  daily: [DAY, { ...DAY, day: "2026-10-02", hit_ratio: null }],
  prices_source: "claude-api skill model table",
  totals: {
    cache_read: 2000,
    cold_start_usd: 1.5,
    cold_starts: 3,
    compaction_usd: 0.42,
    compactions: 2,
    cw_1h: 600,
    cw_5m: 400,
    hit_ratio: 0.75,
    input: 20,
    output: 100,
    pending_tokens: 800,
    spend_usd: 4,
    unsplit: 0,
    usd: 3.92,
    waste_tokens: 1500,
    waste_usd: 0.2,
  },
  waste: [
    {
      cold_start_usd: 1.5,
      cold_starts: 3,
      key: "s3",
      wasted_calls: 1,
      wasted_tokens: 1500,
      wasted_usd: 0.2,
    },
  ],
};

describe("TokenClassesPanel", () => {
  it("shows tiles, the class charts and the waste and compaction tables", () => {
    render(view.render(DATA, { index: INDEX }));
    const tiles = within(screen.getByRole("list", { name: "Cache summary" }));
    expect(tiles.getByText("75.0%")).toBeInTheDocument();
    expect(tiles.getByText("$0.20")).toBeInTheDocument();
    expect(tiles.getByText("3")).toBeInTheDocument();
    expect(tiles.getByText("$0.42")).toBeInTheDocument();
    for (const name of [
      "Cost per class per day",
      "Cache-write tokens per day",
      "Cache hit ratio per day",
    ]) {
      expect(screen.getByRole("img", { name })).toBeInTheDocument();
    }
    expect(screen.getByText("Waste = no call within 1 h.")).toBeInTheDocument();
    expect(screen.getByText("s3")).toBeInTheDocument();
    expect(screen.getByText("write 1h $")).toBeInTheDocument();
    expect(screen.getByText("auto")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Per day, every class" }),
    ).toBeInTheDocument();
    expect(view.name).toBe("token_classes");
    expect(view.order).toBe(66);
  });

  it("dashes a missing hit ratio", () => {
    render(
      view.render(
        { ...DATA, totals: { ...DATA.totals, hit_ratio: null } },
        { index: INDEX },
      ),
    );
    const tiles = within(screen.getByRole("list", { name: "Cache summary" }));
    expect(tiles.getByText("—")).toBeInTheDocument();
  });
});
