import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { ErrorsPanelData } from "./errors-panel.tsx";

import { INDEX } from "../../../test/tokens-fixture.ts";
import { view } from "../panels/errors-view.tsx";

const TS = 1_790_000_000;

const DATA: ErrorsPanelData = {
  api_error_types: [
    { count: 4, last_ts: TS, sessions: 2, type: "rate_limit" },
    { count: 1, last_ts: TS, sessions: 1, type: "overloaded" },
  ],
  api_errors: [
    {
      count: 2,
      detail: "usage_limit_reached",
      last_ts: TS,
      type: "rate_limit",
    },
  ],
  caption: "API errors as the transcript logged them.",
  daily: [
    {
      api_errors: 4,
      calls: 5,
      day: "2026-10-01",
      error_rate: 0.6,
      interrupts: 1,
      rate_limits: 3,
      tool_errors: 3,
    },
    {
      api_errors: 0,
      calls: 0,
      day: "2026-10-02",
      error_rate: null,
      interrupts: 3,
      rate_limits: 0,
      tool_errors: 0,
    },
  ],
  error_kinds: [{ count: 2, error_kind: "exit_code", rate: 0.25, share: 0.5 }],
  error_tools: [
    {
      calls: 4,
      error_rate: 0.75,
      errors: 3,
      family: "git status",
      name: "Bash",
    },
  ],
  recent: [
    {
      error_kind: "tool_error",
      family: "Read:file",
      key: "s1/agent-a",
      name: "Read",
      target: "/r/a.py",
      ts: TS,
    },
    {
      error_kind: "",
      family: "git status",
      key: "s2",
      name: "Bash",
      target: "",
      ts: TS,
    },
  ],
  totals: {
    api_errors: 5,
    calls: 6,
    error_rate: 4 / 6,
    interrupts: 4,
    last_rate_limit_ts: TS,
    rate_limit_hits: 4,
    rate_limit_sessions: 2,
    tool_errors: 4,
  },
};

describe("ErrorsPanel", () => {
  it("shows the limit tiles, daily charts and every error table", () => {
    render(view.render(DATA, { index: INDEX }));
    const tiles = within(screen.getByRole("list", { name: "Error summary" }));
    expect(
      tiles.getByText("rate-limit / usage-limit hits"),
    ).toBeInTheDocument();
    expect(tiles.getByText("66.7%")).toBeInTheDocument();
    expect(tiles.getByText(/in 2 sessions, last/)).toBeInTheDocument();
    expect(
      screen.getByRole("img", { name: "API errors and interrupts per day" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("img", { name: "Tool error rate per day" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("API errors as the transcript logged them."),
    ).toBeInTheDocument();
    expect(screen.getByText("usage_limit_reached")).toBeInTheDocument();
    expect(screen.getByText("overloaded")).toBeInTheDocument();
    expect(screen.getByText("75.0%")).toBeInTheDocument();
    expect(screen.getByText("/r/a.py")).toBeInTheDocument();
    expect(screen.getAllByText("—").length).toBeGreaterThan(1);
    expect(view.name).toBe("errors");
    expect(view.order).toBe(88);
  });

  it("dashes the rate and the last hit when there is nothing", () => {
    render(
      view.render(
        {
          ...DATA,
          totals: {
            ...DATA.totals,
            error_rate: null,
            last_rate_limit_ts: null,
            rate_limit_hits: 0,
          },
        },
        { index: INDEX },
      ),
    );
    const tiles = within(screen.getByRole("list", { name: "Error summary" }));
    expect(tiles.getByText("—")).toBeInTheDocument();
    expect(tiles.getByText("no hits")).toBeInTheDocument();
  });
});
