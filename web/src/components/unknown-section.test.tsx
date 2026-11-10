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
    expect(screen.getByRole("progressbar", { name: /Looking for/ })).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText("127.0.0.1:8798")).toBeInTheDocument();
    });
    expect(screen.getByText(/issue_dashboard/)).toBeInTheDocument();
    // A root-owned listener has no visible process; mark why, not nothing.
    expect(
      screen.getByRole("img", { name: "process not visible to this user" }),
    ).toHaveTextContent("🙈");
    expect(screen.getByText("new-thing.service")).toBeInTheDocument();
    // The scope filter offers the same glyph, so look in the body cell.
    expect(
      within(screen.getAllByRole("table")[1]!).getAllByRole("cell")[0],
    ).toContainElement(screen.getAllByRole("img", { name: "user" }).at(-1)!);
    expect(screen.getAllByRole("img", { name: "user" }).at(-1)).toHaveTextContent("$");
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

  it("paints an unexpected scope as a bullet, its word spoken", async () => {
    vi.spyOn(api, "fetchUnknown").mockResolvedValue({
      listeners: [],
      units: [{ name: "odd.service", scope: "machine" }],
    });
    render(<UnknownSection />);
    await screen.findByText("odd.service");
    // Painted in the body cell and in the scope filter's option alike.
    const glyphs = screen.getAllByRole("img", { name: "machine" });
    for (const glyph of glyphs) {
      expect(glyph).toHaveTextContent("•");
    }
  });

  it("marks when a search matches no listener or user unit", async () => {
    vi.spyOn(api, "fetchUnknown").mockResolvedValue({
      listeners: [{ address: "0.0.0.0", port: 8798, process: "a" }],
      units: [{ name: "x.timer", scope: "user" }],
    });
    const user = userEvent.setup();
    render(<UnknownSection />);
    await screen.findByText("x.timer");
    await user.type(screen.getByLabelText("Search Listener"), "zzz");
    await user.type(screen.getByLabelText("Search Unit"), "zzz");
    expect(
      screen.getAllByRole("cell", { name: "No rows match the current filters." }),
    ).toHaveLength(2);
    expect(screen.queryByText("0.0.0.0:8798")).not.toBeInTheDocument();
    expect(screen.queryByText("x.timer")).not.toBeInTheDocument();
  });

  it("marks everything declared when nothing is left over", async () => {
    vi.spyOn(api, "fetchUnknown").mockResolvedValue({ listeners: [], units: [] });
    render(<UnknownSection />);
    expect(
      await screen.findByRole("status", {
        name: "Every listening port and user unit is declared",
      }),
    ).toHaveTextContent("✓");
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
    expect(screen.queryByRole("heading", { name: "Listening ports" })).not.toBeInTheDocument();
  });

  it("shows a failed read", async () => {
    vi.spyOn(api, "fetchUnknown").mockRejectedValue(new Error("boom"));
    render(<UnknownSection />);
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveAccessibleName(/boom/);
    });
    expect(screen.queryByRole("progressbar")).not.toBeInTheDocument();
  });
});

it("does not set state after unmount", async () => {
  const pending = Promise.withResolvers<never>();
  vi.spyOn(api, "fetchUnknown").mockReturnValue(pending.promise);
  const { unmount } = render(<UnknownSection />);
  unmount();
  pending.reject(new Error("aborted"));
  await new Promise((resolve) => setTimeout(resolve, 0));
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
});
