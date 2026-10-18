import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { PromptCostPanelData } from "./prompt-cost-panel.tsx";

import { INDEX } from "../../../test/tokens-fixture.ts";
import { view } from "../panels/prompt-cost-view.tsx";

const DATA: PromptCostPanelData = {
  caption: "USD per user prompt = usd_own + usd_sub.",
  daily: [
    { day: "2026-09-28", mean_usd: 2, median_usd: 1, prompts: 3, usd: 6 },
    { day: "2026-09-29", mean_usd: 4, median_usd: 4, prompts: 1, usd: 4 },
  ],
  filtered_by: "date range on the prompt's time",
  histogram: [
    { bucket: "< $0.10", prompts: 1 },
    { bucket: "$1-2", prompts: 2 },
  ],
  prompts: [
    {
      active_s: 600,
      calls: 12,
      idx: 0,
      key: "s1",
      text: "fix a",
      total: 5,
      ts: 1_760_000_000,
      usd: 5,
      usd_own: 2,
      usd_sub: 3,
    },
    {
      active_s: 5,
      calls: 1,
      idx: 1,
      key: "s1",
      text: "",
      total: 0.05,
      ts: 1_760_000_100,
      usd: 0.05,
      usd_own: 0.05,
      usd_sub: 0,
    },
  ],
  totals: {
    mean_usd: 2.5,
    median_usd: 1.25,
    prompts: 4,
    top10_share: 0.8,
    usd: 10,
  },
};

describe("PromptCostPanel", () => {
  it("shows the tiles, both charts and the costliest prompts", () => {
    render(view.render(DATA, { index: INDEX }));
    const tiles = within(
      screen.getByRole("list", { name: "Prompt cost summary" }),
    );
    expect(tiles.getByText("$1.25")).toBeInTheDocument();
    expect(tiles.getByText("$2.50")).toBeInTheDocument();
    expect(tiles.getByText("80.0%")).toBeInTheDocument();
    expect(tiles.getByText("4")).toBeInTheDocument();
    expect(
      screen.getByRole("img", { name: "USD per prompt per day" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("img", { name: "Prompts by cost" }),
    ).toBeInTheDocument();
    expect(screen.getByText(/on the prompt's time/u)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "fix a" })).toHaveAttribute(
      "href",
      "#/tokens/s/s1",
    );
    expect(screen.getByRole("link", { name: "(no text)" })).toBeInTheDocument();
    expect(screen.getByText("10m")).toBeInTheDocument();
    expect(view.name).toBe("prompts");
    expect(view.order).toBe(82);
  });

  it("dashes the averages when no prompt is in range", () => {
    render(
      view.render(
        {
          ...DATA,
          prompts: [],
          totals: {
            mean_usd: null,
            median_usd: null,
            prompts: 0,
            top10_share: null,
            usd: 0,
          },
        },
        { index: INDEX },
      ),
    );
    const tiles = within(
      screen.getByRole("list", { name: "Prompt cost summary" }),
    );
    expect(tiles.getAllByText("—")).toHaveLength(3);
  });
});
