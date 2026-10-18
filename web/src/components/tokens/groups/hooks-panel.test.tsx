import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { HookRow, HooksPanelData } from "./hooks-panel.tsx";

import { INDEX } from "../../../test/tokens-fixture.ts";
import { view } from "../panels/hooks-view.tsx";

const HOOK: HookRow = {
  blocks: 0,
  carry_usd: 0.5,
  create_usd: 0.25,
  errors: 2,
  fires: 8,
  hook: "PreToolUse:Bash",
  injected_usd: 0.75,
  mean_ms: 8.75,
  messages: 4,
  retry_usd: 0,
  runtime_s: 0.07,
  script: "time_cap.sh",
  tokens: 200,
  total_usd: 0.75,
};

const DATA: HooksPanelData = {
  budget: [
    {
      budget_s: 1,
      command: "bash /h/.claude/hooks/task_size_u...",
      event: "UserPromptSubmit",
      over_s: 0.2,
      status: "OVER",
      time_s: 1.2,
    },
  ],
  budget_file: {
    caption: "Last run of the hook budget gate.",
    found: true,
    mtime: 1_790_000_000,
    over: 1,
    path: "/h/.claude/state/hook_budget_result.txt",
  },
  caption: "Per hook (hookName + script).",
  daily: [
    { day: "2026-10-01", injected_usd: 0.5, retry_usd: 1 },
    { day: "2026-10-02", injected_usd: 0.25, retry_usd: 0 },
  ],
  hooks: [
    HOOK,
    {
      ...HOOK,
      blocks: 2,
      fires: 0,
      hook: "Stop",
      mean_ms: null,
      retry_usd: 1.5,
      script: "",
      total_usd: 1.5,
    },
  ],
  stop_bounces: [
    { count: 2, hook: "Stop", retry_usd: 1.5, script: "status_tag_stop.py" },
  ],
  totals: {
    blocks: 2,
    errors: 2,
    fires: 8,
    injected_usd: 0.75,
    retry_usd: 1.5,
    runtime_s: 0.07,
    spend_usd: 10,
    tokens: 200,
    total_usd: 2.25,
  },
};

describe("HooksPanel", () => {
  it("shows tiles, the daily cost, per-hook, bounce and budget tables", () => {
    render(view.render(DATA, { index: INDEX }));
    const tiles = within(screen.getByRole("list", { name: "Hook summary" }));
    expect(tiles.getByText("$2.25")).toBeInTheDocument();
    expect(tiles.getByText("22.5%")).toBeInTheDocument();
    expect(tiles.getByText("8")).toBeInTheDocument();
    expect(
      screen.getByRole("img", { name: "Hook cost per day" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Per hook (hookName + script)."),
    ).toBeInTheDocument();
    expect(screen.getByText("time_cap.sh")).toBeInTheDocument();
    expect(screen.getByText("8.8 ms")).toBeInTheDocument();
    expect(screen.getAllByText("—").length).toBeGreaterThan(1);
    expect(screen.getByText("status_tag_stop.py")).toBeInTheDocument();
    expect(screen.getByText("OVER")).toBeInTheDocument();
    expect(
      screen.getByText("Last run of the hook budget gate."),
    ).toBeInTheDocument();
    expect(view.name).toBe("hooks");
    expect(view.order).toBe(62);
  });

  it("says so when the budget file is missing and there was no spend", () => {
    render(
      view.render(
        {
          ...DATA,
          budget: [],
          budget_file: { ...DATA.budget_file, found: false, mtime: null },
          totals: { ...DATA.totals, runtime_s: 125, spend_usd: 0 },
        },
        { index: INDEX },
      ),
    );
    expect(screen.getByText(/No budget-gate result at/)).toBeInTheDocument();
    const tiles = within(screen.getByRole("list", { name: "Hook summary" }));
    expect(tiles.getByText("—")).toBeInTheDocument();
    expect(tiles.getByText("2m")).toBeInTheDocument();
  });
});
