import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { Rationale } from "../lib/types.ts";

import * as api from "../lib/api.ts";
import { WhyPanel } from "./why-panel.tsx";

const FULL: Rationale = {
  artifacts: [
    {
      excerpt: "Persistent=true on purpose (flipped 2026-08-12).",
      kind: "unit-comment",
      label: "leetcode-guard.timer",
      source: "systemctl user cat leetcode-guard.timer",
    },
  ],
  rules: [
    {
      added: "2026-03-01",
      cost_of_bypass: "sudo chattr -i, then beat the guard to the write.",
      id: "shutdown.morning-end-hour",
      ratchet: "LATER only -- the opposite direction from the evening hours.",
      supersedes: [],
      why: "Closes the small-hours window.",
    },
  ],
  signals: [],
  subsystem: "shutdown",
};

describe("WhyPanel", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("shows both the written rule and the quoted artifact", async () => {
    vi.spyOn(api, "fetchWhy").mockResolvedValue(FULL);
    render(<WhyPanel id="shutdown" />);
    await waitFor(() => {
      expect(screen.getByText("shutdown.morning-end-hour")).toBeInTheDocument();
    });
    expect(screen.getByText("Closes the small-hours window.")).toBeInTheDocument();
    expect(screen.getByText(/opposite direction/)).toBeInTheDocument();
    expect(screen.getByText(/Persistent=true on purpose/)).toBeInTheDocument();
  });

  it("omits the ratchet and cost lines when a rule has none", async () => {
    vi.spyOn(api, "fetchWhy").mockResolvedValue({
      ...FULL,
      rules: [{ ...FULL.rules[0]!, cost_of_bypass: "", ratchet: "" }],
    });
    render(<WhyPanel id="x" />);
    await waitFor(() => {
      expect(screen.getByText("shutdown.morning-end-hour")).toBeInTheDocument();
    });
    expect(screen.queryByText("Ratchet")).not.toBeInTheDocument();
    expect(screen.queryByText("Cost of bypass")).not.toBeInTheDocument();
  });

  it("renders a sidecar warning without hiding the artifacts", async () => {
    vi.spyOn(api, "fetchWhy").mockResolvedValue({
      ...FULL,
      rules: [],
      signals: [
        {
          code: "rationale-malformed",
          level: "warn",
          message: "shutdown.json has no 'rules' object",
        },
      ],
    });
    render(<WhyPanel id="x" />);
    await waitFor(() => {
      expect(screen.getByText(/no 'rules' object/)).toBeInTheDocument();
    });
    expect(screen.getByText(/Persistent=true on purpose/)).toBeInTheDocument();
  });

  it("says plainly when nothing is recorded anywhere", async () => {
    vi.spyOn(api, "fetchWhy").mockResolvedValue({
      artifacts: [],
      rules: [],
      signals: [],
      subsystem: "x",
    });
    render(<WhyPanel id="x" />);
    await waitFor(() => {
      expect(screen.getByText(/No rationale is recorded/)).toBeInTheDocument();
    });
  });

  it("shows a loading state, then the error when the read fails", async () => {
    vi.spyOn(api, "fetchWhy").mockRejectedValue(new Error("boom"));
    render(<WhyPanel id="x" />);
    expect(screen.getByText(/Reading rationale/)).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText(/boom/)).toBeInTheDocument();
    });
  });

  it("does not set state after unmount when aborted", async () => {
    const pending = Promise.withResolvers<never>();
    vi.spyOn(api, "fetchWhy").mockReturnValue(pending.promise);
    const { unmount } = render(<WhyPanel id="x" />);
    unmount();
    pending.reject(new Error("aborted"));
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(screen.queryByText(/aborted/)).not.toBeInTheDocument();
  });
});
