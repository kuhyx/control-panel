import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as api from "../lib/api.ts";
import { UnknownSection } from "./unknown-section.tsx";

describe("UnknownSection", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("lists undeclared listeners and units", async () => {
    vi.spyOn(api, "fetchUnknown").mockResolvedValue({
      listeners: [
        {
          address: "127.0.0.1",
          port: 8798,
          process: ".venv/bin/python -m issue_dashboard",
        },
        { address: "0.0.0.0", port: 52_736, process: "" },
      ],
      units: [{ name: "new-thing.service", scope: "user" }],
    });
    render(<UnknownSection />);
    expect(screen.getByText(/Looking for undeclared/)).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText("127.0.0.1:8798")).toBeInTheDocument();
    });
    expect(screen.getByText(/issue_dashboard/)).toBeInTheDocument();
    // A root-owned listener has no visible process; say why, not nothing.
    expect(
      screen.getByText("process not visible to this user"),
    ).toBeInTheDocument();
    expect(screen.getByText("new-thing.service")).toBeInTheDocument();
  });

  it("says everything is declared when nothing is left over", async () => {
    vi.spyOn(api, "fetchUnknown").mockResolvedValue({ listeners: [], units: [] });
    render(<UnknownSection />);
    await waitFor(() => {
      expect(screen.getByText(/is declared somewhere above/)).toBeInTheDocument();
    });
  });

  it("omits an empty half", async () => {
    vi.spyOn(api, "fetchUnknown").mockResolvedValue({
      listeners: [],
      units: [{ name: "x.timer", scope: "user" }],
    });
    render(<UnknownSection />);
    await waitFor(() => {
      expect(screen.getByText("x.timer")).toBeInTheDocument();
    });
    expect(screen.queryByText("Listening ports")).not.toBeInTheDocument();
  });

  it("shows a failed read", async () => {
    vi.spyOn(api, "fetchUnknown").mockRejectedValue(new Error("boom"));
    render(<UnknownSection />);
    await waitFor(() => {
      expect(screen.getByText(/boom/)).toBeInTheDocument();
    });
    expect(screen.queryByText(/Looking for/)).not.toBeInTheDocument();
  });
});

it("does not set state after unmount", async () => {
  const pending = Promise.withResolvers<never>();
  vi.spyOn(api, "fetchUnknown").mockReturnValue(pending.promise);
  const { unmount } = render(<UnknownSection />);
  unmount();
  pending.reject(new Error("aborted"));
  await new Promise((resolve) => setTimeout(resolve, 0));
  expect(screen.queryByText(/aborted/)).not.toBeInTheDocument();
});
