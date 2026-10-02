import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { JournalTail } from "../lib/types.ts";

import * as api from "../lib/api.ts";
import { JOURNAL_LINES, JournalPanel } from "./journal-panel.tsx";

function tail(over: Partial<JournalTail>): JournalTail {
  return {
    error: "",
    lines: ["one", "two"],
    name: "signal-bot.service",
    ok: true,
    source: "user",
    ...over,
  };
}

describe("JournalPanel", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("reads the last 100 lines of the named source", async () => {
    const spy = vi.spyOn(api, "fetchJournal").mockResolvedValue(tail({}));
    render(<JournalPanel name="signal-bot.service" source="user" />);
    expect(screen.getByText("Reading signal-bot.service…")).toBeInTheDocument();
    await waitFor(() => {
      expect(
        screen.getByText("last 2 line(s) of user/signal-bot.service"),
      ).toBeInTheDocument();
    });
    expect(spy).toHaveBeenCalledWith(
      "user",
      "signal-bot.service",
      JOURNAL_LINES,
      expect.any(AbortSignal),
    );
  });

  it("shows the reader's own error when the read failed", async () => {
    vi.spyOn(api, "fetchJournal").mockResolvedValue(
      tail({ error: "No journal files were found.", lines: [], ok: false }),
    );
    render(<JournalPanel name="x.service" source="system" />);
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("No journal files");
    });
  });

  it("still says something when a failed read gave no reason", async () => {
    vi.spyOn(api, "fetchJournal").mockResolvedValue(tail({ ok: false }));
    render(<JournalPanel name="gitea" source="docker" />);
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("the read failed");
    });
  });

  it("shows a transport error", async () => {
    vi.spyOn(api, "fetchJournal").mockRejectedValue(new Error("404"));
    render(<JournalPanel name="x" source="user" />);
    await waitFor(() => {
      expect(screen.getByText(/404/)).toBeInTheDocument();
    });
  });
});

it("does not set state after the panel closes mid-read", async () => {
  const pending = Promise.withResolvers<never>();
  vi.spyOn(api, "fetchJournal").mockReturnValue(pending.promise);
  const { unmount } = render(<JournalPanel name="x" source="user" />);
  unmount();
  pending.reject(new Error("aborted"));
  await new Promise((resolve) => setTimeout(resolve, 0));
  expect(screen.queryByText(/aborted/)).not.toBeInTheDocument();
});
