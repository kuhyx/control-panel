import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as api from "../lib/api.ts";
import { UnknownSection } from "./unknown-section.tsx";

describe("UnknownSection", () => {
  beforeEach(() => {
    globalThis.history.replaceState(null, "", "#");
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

  it("sorts listeners by port number, not by address text", async () => {
    vi.spyOn(api, "fetchUnknown").mockResolvedValue({
      listeners: [
        { address: "0.0.0.0", port: 8798, process: "a" },
        { address: "127.0.0.1", port: 952, process: "b" },
        { address: "192.0.2.1", port: 22, process: "c" },
      ],
      units: [],
    });
    const user = userEvent.setup();
    render(<UnknownSection />);
    await screen.findByText("0.0.0.0:8798");
    const ports = (): string[] => {
      const cells = within(screen.getByRole("table")).getAllByRole("rowheader");
      return cells.map((cell) => cell.textContent);
    };
    await user.click(screen.getByRole("button", { name: /Listener/ }));
    expect(ports()).toEqual(["192.0.2.1:22", "127.0.0.1:952", "0.0.0.0:8798"]);
    await user.click(screen.getByRole("button", { name: /Listener/ }));
    expect(ports()).toEqual(["0.0.0.0:8798", "127.0.0.1:952", "192.0.2.1:22"]);
  });

  it("says so when a search matches no listener or user unit", async () => {
    vi.spyOn(api, "fetchUnknown").mockResolvedValue({
      listeners: [{ address: "0.0.0.0", port: 8798, process: "a" }],
      units: [{ name: "x.timer", scope: "user" }],
    });
    const user = userEvent.setup();
    render(<UnknownSection />);
    await screen.findByText("x.timer");
    await user.type(screen.getByLabelText("Search Listener"), "zzz");
    await user.type(screen.getByLabelText("Search Unit"), "zzz");
    expect(screen.getAllByText("No rows match the current filters.")).toHaveLength(2);
    expect(screen.queryByText("0.0.0.0:8798")).not.toBeInTheDocument();
    expect(screen.queryByText("x.timer")).not.toBeInTheDocument();
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
