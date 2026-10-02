import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as api from "../lib/api.ts";
import { LogViewer } from "./log-viewer.tsx";

describe("LogViewer", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("says the 57 MB file is never read whole", async () => {
    vi.spyOn(api, "fetchLog").mockResolvedValue({
      id: "hosts-monitor",
      lines: ["one", "two"],
      path: "/var/log/hosts-file-monitor.log",
      total_bytes: 57_282_668,
      truncated: true,
    });
    render(<LogViewer id="hosts-monitor" />);
    await waitFor(() => {
      expect(screen.getByText(/never read whole/)).toBeInTheDocument();
    });
    expect(screen.getByText(/54.6 MB/)).toBeInTheDocument();
  });

  it("reports a plain line count for a short log", async () => {
    vi.spyOn(api, "fetchLog").mockResolvedValue({
      id: "small",
      lines: ["only"],
      total_bytes: 5,
      truncated: false,
    });
    render(<LogViewer id="small" />);
    await waitFor(() => {
      expect(screen.getByText("1 line(s)")).toBeInTheDocument();
    });
  });

  it("surfaces a server note", async () => {
    vi.spyOn(api, "fetchLog").mockResolvedValue({
      id: "j",
      lines: [],
      note: "journal reads are not implemented yet",
      total_bytes: null,
      truncated: false,
    });
    render(<LogViewer id="j" />);
    await waitFor(() => {
      expect(screen.getByText(/not implemented/)).toBeInTheDocument();
    });
  });

  it("shows a loading state and then the error when the read fails", async () => {
    vi.spyOn(api, "fetchLog").mockRejectedValue(new Error("boom"));
    render(<LogViewer id="x" />);
    expect(screen.getByText(/Loading x/)).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText(/boom/)).toBeInTheDocument();
    });
  });
});

it("does not set state after unmount when the read is aborted", async () => {
  const pending = Promise.withResolvers<never>();
  vi.spyOn(api, "fetchLog").mockReturnValue(pending.promise);
  const { unmount } = render(<LogViewer id="x" />);
  unmount();
  pending.reject(new Error("aborted"));
  await new Promise((resolve) => setTimeout(resolve, 0));
  expect(screen.queryByText(/aborted/)).not.toBeInTheDocument();
});

it("renders a journal-kind log through the journal reader", async () => {
  vi.spyOn(api, "fetchLog").mockResolvedValue({
    error: "",
    lines: ["started"],
    name: "steam-backlog-enforcer.service",
    ok: true,
    source: "system",
  });
  render(<LogViewer id="steam-enforcer" />);
  await waitFor(() => {
    expect(
      screen.getByRole("heading", { name: "steam-backlog-enforcer.service" }),
    ).toBeInTheDocument();
  });
  expect(screen.getByText("started")).toBeInTheDocument();
});
