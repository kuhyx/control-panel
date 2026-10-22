import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "./app.tsx";
import * as api from "./lib/api.ts";
import { STATUS } from "./test/fixture.ts";
import { stubSessionsFetch } from "./test/sessions-fixture.ts";
import { stubTokensFetch } from "./test/tokens-fetch.ts";

function goto(hash: string): void {
  globalThis.location.hash = hash;
  globalThis.dispatchEvent(new HashChangeEvent("hashchange"));
}

describe("App", () => {
  beforeEach(() => {
    globalThis.location.hash = "";
    vi.spyOn(api, "fetchStatus").mockResolvedValue(STATUS);
    vi.spyOn(api, "fetchUnknown").mockResolvedValue({ listeners: [], units: [] });
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it("shows a reading state, then the overview", async () => {
    render(<App />);
    expect(screen.getByText("Reading…")).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByRole("table")).toBeInTheDocument();
    });
    expect(screen.getByText(/archlinux/)).toBeInTheDocument();
    expect(screen.getByText(/1557 ms/)).toBeInTheDocument();
  });

  it("routes to the token page", async () => {
    stubTokensFetch();
    render(<App />);
    goto("#/tokens");
    expect(
      await screen.findByRole("heading", { name: "Claude Code spend" }),
    ).toBeInTheDocument();
    vi.unstubAllGlobals();
  });

  it("routes to the sessions tab", async () => {
    stubSessionsFetch();
    render(<App />);
    goto("#/tokens/sessions");
    expect(
      await screen.findByRole("heading", { name: "Claude Code sessions" }),
    ).toBeInTheDocument();
    vi.unstubAllGlobals();
  });

  it("routes to a subsystem and back", async () => {
    render(<App />);
    await waitFor(() => {
      expect(screen.getByRole("table")).toBeInTheDocument();
    });
    goto("#/s/hosts");
    await waitFor(() => {
      expect(
        screen.getByRole("heading", { name: "Hosts / DNS blocking" }),
      ).toBeInTheDocument();
    });
    goto("#/");
    await waitFor(() => {
      expect(screen.getByText("2 finding(s)")).toBeInTheDocument();
    });
  });

  it("says so when a subsystem id does not exist", async () => {
    render(<App />);
    goto("#/s/ghost");
    await waitFor(() => {
      expect(screen.getByText(/No such subsystem: ghost/)).toBeInTheDocument();
    });
  });

  it("routes to the log viewer", async () => {
    vi.spyOn(api, "fetchLog").mockResolvedValue({
      id: "hosts-monitor",
      lines: ["a line"],
      path: "/var/log/hosts-file-monitor.log",
      total_bytes: 10,
      truncated: false,
    });
    render(<App />);
    goto("#/logs/hosts-monitor");
    await waitFor(() => {
      expect(screen.getByText("a line")).toBeInTheDocument();
    });
  });

  it("surfaces a failed read as an alert", async () => {
    vi.spyOn(api, "fetchStatus").mockRejectedValue(new Error("server down"));
    render(<App />);
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/server down/);
    });
  });

  it("polls, and stops polling when unmounted", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const spy = vi.spyOn(api, "fetchStatus").mockResolvedValue(STATUS);
    const { unmount } = render(<App />);
    await vi.advanceTimersByTimeAsync(5000);
    expect(spy.mock.calls.length).toBeGreaterThanOrEqual(2);
    const afterMount = spy.mock.calls.length;
    unmount();
    await vi.advanceTimersByTimeAsync(20_000);
    expect(spy.mock.calls).toHaveLength(afterMount);
  });
});

it("does not report an error for a read aborted by unmounting", async () => {
  const pending = Promise.withResolvers<never>();
  vi.spyOn(api, "fetchStatus").mockReturnValue(pending.promise);
  const { unmount } = render(<App />);
  unmount();
  pending.reject(new Error("aborted"));
  await new Promise((resolve) => setTimeout(resolve, 0));
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
});

it("lists what the manifest does not cover below the overview", async () => {
  globalThis.location.hash = "";
  vi.spyOn(api, "fetchStatus").mockResolvedValue(STATUS);
  vi.spyOn(api, "fetchUnknown").mockResolvedValue({
    listeners: [{ address: "0.0.0.0", port: 52_736, process: "" }],
    units: [],
  });
  render(<App />);
  expect(
    await screen.findByRole("heading", { name: "Not in the manifest" }),
  ).toBeInTheDocument();
  expect(await screen.findByText("0.0.0.0:52736")).toBeInTheDocument();
  vi.restoreAllMocks();
});
