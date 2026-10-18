import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { ContextGrowthData } from "./context-growth-panel.tsx";

import { INDEX } from "../../../test/tokens-fixture.ts";
import { view } from "../panels/context-growth-view.tsx";

const CURVE = {
  chart: 1,
  key: "s1",
  max_context: 310_000,
  points: [
    { call: 1, context: 1000 },
    { call: 10, context: 310_000 },
  ],
  title: "fix a",
  usd: 4,
};

const DATA: ContextGrowthData = {
  caption: "Context = the call's whole prompt.",
  crossings: [
    {
      calls: 3,
      calls_over_250k: 2,
      calls_over_300k: 1,
      key: "s3",
      max_context: 310_000,
      title: "",
      usd: 2,
      usd_over_300k: 1,
    },
    {
      calls: 1,
      calls_over_250k: 1,
      calls_over_300k: 0,
      key: "s9",
      max_context: 260_000,
      title: "long talk",
      usd: 1,
      usd_over_300k: 0,
    },
  ],
  growth: [
    CURVE,
    { ...CURVE, key: "s2", title: "" },
    { ...CURVE, key: "s4" },
    { ...CURVE, chart: 2, key: "s5" },
  ],
  handoffs: [
    {
      detail: "/h/handoff/x.md",
      key: "s3",
      source: "write",
      ts: 1_790_000_000,
    },
  ],
  histogram: [
    { bucket: "0-50k", calls: 3, usd: 1 },
    { bucket: "300k+", calls: 2, usd: 3 },
  ],
  percentiles: { p50: 100_000, p90: 400_000, p99: null },
};

describe("ContextGrowthPanel", () => {
  it("shows percentiles, the histogram, growth charts and both tables", () => {
    render(view.render(DATA, { index: INDEX }));
    const tiles = within(
      screen.getByRole("list", { name: "Context percentiles" }),
    );
    expect(tiles.getByText("100,000")).toBeInTheDocument();
    expect(tiles.getByText("400,000")).toBeInTheDocument();
    expect(tiles.getByText("—")).toBeInTheDocument();
    expect(
      screen.getByRole("img", { name: "Calls per context size" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("img", { name: "Context growth, sessions 1-3" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("img", { name: "Context growth, sessions 4-4" }),
    ).toBeInTheDocument();
    expect(screen.getByText("/h/handoff/x.md")).toBeInTheDocument();
    expect(screen.getByText("long talk")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Keys that crossed 250k" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Context = the call's whole prompt."),
    ).toBeInTheDocument();
    expect(view.name).toBe("context_growth");
    expect(view.order).toBe(68);
  });
});
