import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { OutputData } from "./output-panel.tsx";

import { INDEX } from "../../../test/tokens-fixture.ts";
import { view } from "../panels/output-view.tsx";

const DAY = {
  day: "2026-10-01",
  output: 1000,
  output_share: 0.1,
  output_usd: 0.02,
  spend_usd: 0.2,
  text: 300,
  think: 600,
  tool: 100,
};

const DATA: OutputData = {
  caption: "The split is an estimate.",
  daily: [DAY, { ...DAY, day: "2026-10-02", output_share: null }],
  longest: [
    {
      key: "s3",
      model: "claude-opus-5-5",
      output: 44_911,
      output_usd: 0.9,
      text: 36,
      think: 44_776,
      tool: 99,
      ts: 1_790_000_000,
      usd: 1.2,
    },
    {
      key: "s4",
      model: "claude-opus-5-5",
      output: 12,
      output_usd: 0.1,
      text: null,
      think: null,
      tool: null,
      ts: 1_790_000_100,
      usd: 0.3,
    },
  ],
  totals: {
    output: 2000,
    output_share: 0.25,
    output_usd: 2.5,
    spend_usd: 10,
    text: 600,
    think: 1200,
    tool: 200,
  },
};

describe("OutputPanel", () => {
  it("shows tiles, the split and share charts and the longest replies", () => {
    render(view.render(DATA, { index: INDEX }));
    const tiles = within(screen.getByRole("list", { name: "Output summary" }));
    expect(tiles.getByText("$2.50")).toBeInTheDocument();
    expect(tiles.getByText("25.0%")).toBeInTheDocument();
    expect(tiles.getByText("60.0%")).toBeInTheDocument();
    expect(
      screen.getByRole("img", { name: "Output tokens per day" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("img", { name: "Output share of spend per day" }),
    ).toBeInTheDocument();
    expect(screen.getByText("44,776")).toBeInTheDocument();
    expect(screen.getByText("The split is an estimate.")).toBeInTheDocument();
    expect(view.name).toBe("output");
    expect(view.order).toBe(80);
  });

  it("dashes shares when nothing was spent", () => {
    render(
      view.render(
        {
          ...DATA,
          totals: { ...DATA.totals, output: 0, output_share: null },
        },
        { index: INDEX },
      ),
    );
    const tiles = within(screen.getByRole("list", { name: "Output summary" }));
    expect(tiles.getAllByText("—")).toHaveLength(2);
  });
});
