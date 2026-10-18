import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  AB,
  CONTEXT,
  EFFICIENCY,
  INDEX,
  LEVERS,
  OVERVIEW,
  SESSIONS,
} from "../../test/tokens-fixture.ts";
import { AbBanner, AbPanel } from "./ab-panel.tsx";
import { ContextPanel } from "./context-panel.tsx";
import { EfficiencyPanel } from "./efficiency-panel.tsx";
import { LeversPanel } from "./levers-panel.tsx";
import { SessionsPanel } from "./sessions-panel.tsx";
import { SpendPanel } from "./spend-panel.tsx";

function row(name: string): HTMLElement {
  const cell = screen.getByRole("cell", { name });
  const found = cell.closest("tr");
  if (found === null) throw new Error(`no row for ${name}`);
  return found;
}

describe("AbPanel", () => {
  it("colours the banner by level", () => {
    render(<AbBanner banner={{ level: "red", text: "quality drop" }} />);
    expect(screen.getByRole("status")).toHaveClass("ab-banner", "ab-red");
  });

  it("fills the present arm and dashes the missing one", () => {
    render(<AbPanel data={AB} />);
    expect(screen.getByText(/3 assignments not/)).toBeInTheDocument();
    expect(row("n")).toHaveTextContent("n120");
    expect(row("cost per agent (mean, 95% CI)")).toHaveTextContent("$1.00 [$0.50, $2.00]—");
    expect(row("duration (mean)")).toHaveTextContent("1m—");
    const redo = row("redo rate (similar Agent re-dispatched)");
    expect(redo).toHaveTextContent("0.0% [0.0%, 10.0%]—-5.0% [-20.0%, 10.0%]");
    expect(row("error / aborted rate")).toHaveTextContent("——");
    expect(row("parent session end tag")).toHaveTextContent("DONE 3, RUNNING 1—");
  });

  it("tolerates a payload with no diffs or unjoined count", () => {
    render(<AbPanel data={{ arms: {}, banner: AB.banner }} />);
    expect(screen.getByText(/0 assignments not/)).toBeInTheDocument();
  });
});

describe("ContextPanel", () => {
  it("lists every file with its cost, size and warning", () => {
    render(<ContextPanel data={CONTEXT} />);
    expect(screen.getByText(/812 calls\/day/)).toBeInTheDocument();
    expect(screen.getByText(/Total \$0\.25\/day/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "~/.claude/CLAUDE.md" })).toHaveAttribute(
      "href",
      `#/tokens/f/${encodeURIComponent("/home/kuhy/.claude/CLAUDE.md")}`,
    );
    expect(screen.getByText("over 40k")).toHaveClass("warn-badge");
    expect(row("gone")).toHaveTextContent("0 points");
  });
});

describe("EfficiencyPanel", () => {
  it("totals numeric cells and skips the rest", () => {
    render(<EfficiencyPanel data={EFFICIENCY} />);
    expect(screen.getByText(/in range: 2,/)).toBeInTheDocument();
    expect(screen.getByText(/3 survived,/)).toBeInTheDocument();
    expect(screen.getByText(/0 pending/)).toBeInTheDocument();
    expect(screen.getByText("Est caption.")).toBeInTheDocument();
  });
});

describe("LeversPanel", () => {
  it("charts applied levers and tabulates them all", () => {
    render(<LeversPanel data={LEVERS} />);
    expect(screen.getByText("Every lever (4)")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "usd_per_call around trim CLAUDE.md" })).toBeInTheDocument();
    expect(screen.queryByRole("img", { name: /around idea/ })).toBeNull();
    // Axis ticks use the metric's own unit.
    expect(screen.getAllByText("$0.500").length).toBeGreaterThan(0);
    expect(screen.getAllByText("$2.0").length).toBeGreaterThan(0);
    expect(screen.getAllByText("50.0%").length).toBeGreaterThan(0);
    expect(screen.getAllByText("4.0K").length).toBeGreaterThan(0);
    expect(screen.getAllByText("0.00").length).toBeGreaterThan(0);
    expect(screen.getAllByText(/· cut the rules/).length).toBeGreaterThan(0);
    const share = within(screen.getByRole("table")).getByText("share lever").closest("tr");
    expect(share).toHaveTextContent("applied——share leveropus_usd_share——0.3ledger");
  });
});

describe("SessionsPanel", () => {
  it("links each session and names its dominant model", () => {
    render(<SessionsPanel data={SESSIONS} />);
    expect(screen.getByText(/Top 50 sessions/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Fix the thing" })).toHaveAttribute(
      "href",
      "#/tokens/s/sess-1",
    );
    const first = row("~/src/a");
    expect(first).toHaveTextContent("sonnet");
    expect(first).toHaveTextContent("DONE");
    const second = screen.getByRole("link", { name: "sess-2" }).closest("tr");
    if (second === null) throw new Error("no row for sess-2");
    // cwd, model and end tag are all unknown.
    expect(within(second).getAllByText("—")).toHaveLength(3);
  });
});

describe("SpendPanel", () => {
  it("shows the tiles and every spend chart", () => {
    render(
      <SpendPanel data={OVERVIEW} index={INDEX} snapshotMetrics={INDEX.snapshot_metrics} />,
    );
    const tiles = within(screen.getByRole("list", { name: "Spend summary" }));
    expect(tiles.getByText("$85.00")).toBeInTheDocument();
    expect(tiles.getByText("$170")).toBeInTheDocument();
    expect(tiles.getByText("1,500")).toBeInTheDocument();
    expect(tiles.getByText("—")).toBeInTheDocument();
    expect(tiles.getByText("2h30")).toBeInTheDocument();
    expect(tiles.getByText(/7 sessions/)).toBeInTheDocument();
    for (const name of [
      "USD per day",
      "USD per week",
      "USD per call",
      "Calls per day",
      "Opus share of USD",
      "Subagent share of USD",
      "Over-budget share (context > 300k)",
      "Prompts per day",
    ]) {
      expect(screen.getByRole("img", { name })).toBeInTheDocument();
    }
  });
});
