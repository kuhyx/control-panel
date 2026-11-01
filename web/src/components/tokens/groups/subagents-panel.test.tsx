import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { AgentGroupRow, SubagentsPanelData } from "./subagents-panel.tsx";

import { INDEX } from "../../../test/tokens-fixture.ts";
import { view } from "../panels/subagents-view.tsx";

const GROUP: AgentGroupRow = {
  active_s: 80,
  agents: 2,
  calls: 40,
  label: "Explore",
  leverage: 0.00002,
  returned_tokens: 300,
  spent_tokens: 15_000_000,
  usd: 3.5,
  wall_s: 4000,
};

const DATA: SubagentsPanelData = {
  by_description: [{ ...GROUP, label: "Find x", leverage: null }],
  by_model: [{ ...GROUP, label: "claude-sonnet-5-5" }],
  by_type: [GROUP],
  caption: "Leverage = returned / spent.",
  routing: {
    ab: [
      { arm: "sonnet", class: "judgment", count: 4, subagent_type: "general" },
    ],
    gap: "",
    hook_runs: 9,
    rewrites: 7,
  },
  totals: { ...GROUP, worktree_agents: 3 },
  worktree: [
    {
      day: "2026-10-01",
      key: "s1",
      sub_key: "s1/agent-b",
      target: "general-purpose [worktree]",
      usd: null,
    },
  ],
};

describe("SubagentsPanel", () => {
  it("shows cost, leverage, worktree agents and routing", () => {
    render(view.render(DATA, { index: INDEX }));
    const tiles = within(
      screen.getByRole("list", { name: "Subagent summary" }),
    );
    expect(tiles.getByText("$3.50")).toBeInTheDocument();
    expect(tiles.getByText("50,000")).toBeInTheDocument();
    expect(tiles.getByText("3")).toBeInTheDocument();
    expect(tiles.getByText("7")).toBeInTheDocument();
    expect(screen.getAllByText("2.00e-5")).toHaveLength(2);
    expect(screen.getAllByText("1h07")).toHaveLength(3);
    expect(screen.getByText("general-purpose [worktree]")).toBeInTheDocument();
    expect(screen.getByText("judgment")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "By description" }),
    ).toBeInTheDocument();
    expect(view.name).toBe("subagents");
  });

  it("names the routing-log gap and dashes an unknown leverage", () => {
    render(
      view.render(
        {
          ...DATA,
          routing: { ...DATA.routing, ab: [], gap: "no agent-ab.jsonl" },
          totals: { ...DATA.totals, leverage: null },
        },
        { index: INDEX },
      ),
    );
    expect(screen.getByText("no agent-ab.jsonl")).toBeInTheDocument();
    const tiles = within(
      screen.getByRole("list", { name: "Subagent summary" }),
    );
    expect(tiles.getByText("—")).toBeInTheDocument();
  });

  it("lists the build A/B log apart from the judgment one", () => {
    const data: SubagentsPanelData = {
      ...DATA,
      routing: {
        ...DATA.routing,
        ab_build: [
          { arm: "opus", class: "build", count: 2, subagent_type: "general" },
        ],
        gap_build: "no build log yet",
      },
    };
    render(view.render(data, { index: INDEX }));
    expect(screen.getByText("Build A/B arms")).toBeInTheDocument();
    expect(screen.getByText("Judgment A/B arms (closed)")).toBeInTheDocument();
    expect(screen.getByText("no build log yet")).toBeInTheDocument();
  });

  it("dashes a zero leverage tile", () => {
    render(
      view.render(
        { ...DATA, totals: { ...DATA.totals, leverage: 0 } },
        { index: INDEX },
      ),
    );
    const tiles = within(
      screen.getByRole("list", { name: "Subagent summary" }),
    );
    expect(tiles.getByText("—")).toBeInTheDocument();
  });
});
