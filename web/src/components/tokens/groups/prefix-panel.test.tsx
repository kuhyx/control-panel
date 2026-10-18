import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { PrefixPanelData } from "./prefix-panel.tsx";

import { INDEX } from "../../../test/tokens-fixture.ts";
import { view } from "../panels/prefix-view.tsx";

const DATA: PrefixPanelData = {
  caption: "Standing prefix = context on every call.",
  filtered_by: "date range only for sizes",
  prunes: [
    {
      bytes: 0,
      delta_bytes: -400,
      path: "/h/.claude/rules/gone.md",
      source: "prune 2026-09-28",
      surface: "rules",
      ts: 1_760_000_000,
    },
    {
      bytes: 50,
      delta_bytes: null,
      path: "/x/topics/a.md",
      source: "git",
      surface: "not standing",
      ts: 1_759_990_000,
    },
  ],
  series: [
    {
      label: "always-loaded files",
      points: [
        { day: "2026-09-28", tokens: 700 },
        { day: "2026-09-30", tokens: 700 },
      ],
    },
    {
      label: "audit estimate (all surfaces)",
      points: [{ day: "2026-09-29", tokens: 5000 }],
    },
  ],
  surfaces: [
    {
      delta_tokens: -500,
      files: 1,
      start_tokens: 1000,
      surface: "global CLAUDE.md",
      tokens: 500,
      usd_per_day: 1.25,
    },
  ],
  totals: {
    audit_tokens: 5000,
    audit_usd_per_day: 4.5,
    calls_per_day: 2889.3,
    files_tokens: 700,
    files_usd_per_day: 0.75,
    price_per_mtok: 0.2,
    pruned_bytes: 2400,
  },
};

describe("PrefixPanel", () => {
  it("shows the tiles, the size chart, surfaces and the prune timeline", () => {
    render(view.render(DATA, { index: INDEX }));
    const tiles = within(screen.getByRole("list", { name: "Prefix summary" }));
    expect(tiles.getByText("5,000")).toBeInTheDocument();
    expect(tiles.getByText("$4.50")).toBeInTheDocument();
    expect(tiles.getByText("$0.75")).toBeInTheDocument();
    expect(tiles.getByText("2,889")).toBeInTheDocument();
    expect(tiles.getByText("2,400")).toBeInTheDocument();
    expect(
      screen.getByRole("img", { name: "Standing prefix tokens over time" }),
    ).toBeInTheDocument();
    expect(screen.getByText(/date range only for sizes/u)).toBeInTheDocument();
    expect(screen.getByText("global CLAUDE.md")).toBeInTheDocument();
    expect(screen.getByText("−500")).toBeInTheDocument();
    expect(screen.getByText("−400")).toBeInTheDocument();
    expect(screen.getByText("/x/topics/a.md")).toBeInTheDocument();
    expect(screen.getAllByText("—").length).toBeGreaterThan(0);
    expect(view.name).toBe("prefix");
    expect(view.order).toBe(64);
  });

  it("dashes the audit tiles when no snapshot is in range", () => {
    render(
      view.render(
        {
          ...DATA,
          surfaces: [{ ...DATA.surfaces[0], delta_tokens: 20 }],
          totals: {
            ...DATA.totals,
            audit_tokens: null,
            audit_usd_per_day: null,
          },
        },
        { index: INDEX },
      ),
    );
    const tiles = within(screen.getByRole("list", { name: "Prefix summary" }));
    expect(tiles.getAllByText("—")).toHaveLength(2);
    expect(screen.getByText("+20")).toBeInTheDocument();
  });
});
