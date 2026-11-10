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
    expect(screen.queryByLabelText("Ratchet")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Cost of bypass")).not.toBeInTheDocument();
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
    // The server's sentence is the note's spoken name; a warning glyph is painted.
    const note = await screen.findByRole("note", { name: /no 'rules' object/ });
    expect(note).toHaveTextContent("⚠");
    expect(screen.getByText(/Persistent=true on purpose/)).toBeInTheDocument();
  });

  it("paints an info signal with its own glyph", async () => {
    vi.spyOn(api, "fetchWhy").mockResolvedValue({
      ...FULL,
      signals: [{ code: "from-sidecar", level: "info", message: "read from the sidecar" }],
    });
    render(<WhyPanel id="x" />);
    const note = await screen.findByRole("note", { name: "read from the sidecar" });
    expect(note).toHaveTextContent("ℹ");
    expect(note).not.toHaveTextContent("sidecar");
  });

  it("speaks an artifact's kind and marks the empty-audit-log placeholder", async () => {
    vi.spyOn(api, "fetchWhy").mockResolvedValue({
      ...FULL,
      artifacts: [
        ...FULL.artifacts,
        {
          excerpt: "no entries recorded",
          kind: "audit-log",
          label: "hosts audit",
          source: "/var/log/hosts-audit.log",
        },
      ],
    });
    const { container } = render(<WhyPanel id="x" />);
    expect(await screen.findByRole("img", { name: "unit-comment" })).toHaveTextContent("📄");
    expect(screen.getByRole("status", { name: "no entries recorded" })).toHaveTextContent("∅");
    // The real excerpt stays verbatim; the placeholder gets no <pre>.
    expect(container.querySelectorAll("pre")).toHaveLength(1);
    expect(screen.queryByText("no entries recorded")).toBeNull();
  });

  it("marks plainly when nothing is recorded anywhere", async () => {
    vi.spyOn(api, "fetchWhy").mockResolvedValue({
      artifacts: [],
      rules: [],
      signals: [],
      subsystem: "x",
    });
    render(<WhyPanel id="x" />);
    expect(
      await screen.findByRole("status", { name: "No rationale is recorded" }),
    ).toHaveTextContent("∅");
  });

  it("shows a loading state, then the error when the read fails", async () => {
    vi.spyOn(api, "fetchWhy").mockRejectedValue(new Error("boom"));
    render(<WhyPanel id="x" />);
    expect(screen.getByRole("progressbar", { name: /Reading rationale/ })).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveAccessibleName(/boom/);
    });
  });

  it("does not set state after unmount when aborted", async () => {
    const pending = Promise.withResolvers<never>();
    vi.spyOn(api, "fetchWhy").mockReturnValue(pending.promise);
    const { unmount } = render(<WhyPanel id="x" />);
    unmount();
    pending.reject(new Error("aborted"));
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
