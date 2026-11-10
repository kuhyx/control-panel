import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  NOW_MS,
  postedBodies,
  SESSIONS,
  stubSessionsFetch,
} from "../../test/sessions-fixture.ts";
import { SessionsPage } from "./sessions-page.tsx";

const now = (): number => NOW_MS;
const writeText = vi.fn<(text: string) => Promise<void>>(() =>
  Promise.resolve(),
);

const box = (id: string): HTMLElement =>
  screen.getByRole("checkbox", { name: `Select ${id}` });
const all = (): HTMLElement =>
  screen.getByRole("checkbox", { name: "Select all shown sessions" });
const bar = (): HTMLElement => screen.getByRole("region", { name: "Bulk actions" });
// The bar paints "☑ N"; "N selected" is its spoken name.
const selected = (): null | string =>
  within(bar()).queryByLabelText(/ selected$/u)?.getAttribute("aria-label") ?? null;
const sessionCalls = (spy: ReturnType<typeof stubSessionsFetch>): number =>
  spy.mock.calls.filter(([path]) => path === "/api/sessions").length;

async function open(
  hash = "#/sessions",
  payload: Parameters<typeof stubSessionsFetch>[0] = SESSIONS,
): Promise<ReturnType<typeof stubSessionsFetch>> {
  globalThis.history.replaceState(null, "", hash);
  const spy = stubSessionsFetch(payload);
  render(<SessionsPage now={now} />);
  await screen.findByRole("checkbox", { name: "Select all shown sessions" });
  return spy;
}

beforeEach(() => {
  writeText.mockReset();
  writeText.mockResolvedValue();
  vi.stubGlobal("navigator", { clipboard: { writeText } });
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("SessionsPage selection", () => {
  it("selects all shown rows from the header, tri-state when partial", async () => {
    await open();
    expect(screen.queryByRole("region", { name: "Bulk actions" })).toBeNull();
    fireEvent.click(box("bravo"));
    expect(all()).toBePartiallyChecked();
    expect(selected()).toBe("1 selected");
    fireEvent.click(all());
    expect(all()).toBeChecked();
    expect(selected()).toBe("4 selected");
    fireEvent.change(screen.getByRole("combobox", { name: "Project" }), { target: { value: "panel" } });
    // Hidden rows drop out of the selection: only what is shown is acted on.
    expect(selected()).toBe("2 selected");
    expect(all()).toBeChecked();
    fireEvent.click(all());
    expect(all()).not.toBeChecked();
    expect(screen.queryByRole("region", { name: "Bulk actions" })).toBeNull();
  });

  it("leaves the header unticked when nothing is shown", async () => {
    await open("#/sessions?q=nothing-matches");
    expect(all()).not.toBeChecked();
    expect(all()).not.toBePartiallyChecked();
  });

  it("does not expand a row when its checkbox is clicked", async () => {
    await open();
    fireEvent.click(box("alpha"));
    expect(screen.getByRole("button", { name: "title of alpha" })).toHaveAttribute(
      "aria-expanded",
      "false",
    );
  });

  it("shift-click selects, then clears, the range from the last click", async () => {
    await open("#/sessions?done=1");
    fireEvent.click(box("bravo"));
    fireEvent.click(box("echo"), { shiftKey: true });
    expect(selected()).toBe("4 selected");
    for (const id of ["bravo", "charlie", "delta", "echo"]) {
      expect(box(id)).toBeChecked();
    }
    fireEvent.click(box("charlie"), { shiftKey: true });
    // charlie was on, so the range echo..charlie goes off.
    expect(selected()).toBe("1 selected");
    expect(box("bravo")).toBeChecked();
  });

  it("shift-click with no visible anchor toggles one row", async () => {
    await open();
    fireEvent.click(box("delta"), { shiftKey: true });
    expect(selected()).toBe("1 selected");
    fireEvent.click(box("alpha"));
    fireEvent.change(screen.getByRole("combobox", { name: "Project" }), { target: { value: "router" } });
    fireEvent.click(box("charlie"), { shiftKey: true });
    expect(selected()).toBe("1 selected");
  });

  it("keeps the selection across a refetch, dropping ids that vanished", async () => {
    const without = SESSIONS.sessions.filter((s) => s.id !== "bravo");
    const spy = await open("#/sessions", [
      SESSIONS,
      { ...SESSIONS, sessions: without },
    ]);
    fireEvent.click(box("alpha"));
    fireEvent.click(box("bravo"));
    expect(selected()).toBe("2 selected");
    fireEvent.click(screen.getByRole("button", { name: "Mark charlie done" }));
    await waitFor(() => {
      expect(screen.queryByRole("checkbox", { name: "Select bravo" })).toBeNull();
    });
    expect(sessionCalls(spy)).toBe(2);
    expect(box("alpha")).toBeChecked();
    expect(selected()).toBe("1 selected");
    fireEvent.click(within(bar()).getByRole("button", { name: "Copy commands" }));
    expect(
      await within(bar()).findByRole("status", { name: "Copied 1 command" }),
    ).toBeInTheDocument();
    expect(writeText).toHaveBeenCalledWith(
      "cd '/home/kuhy/src/alpha' && claude --resume alpha",
    );
  });

  it("disables bulk Resume with more than five selected", async () => {
    await open("#/sessions?done=1");
    fireEvent.click(all());
    expect(selected()).toBe("7 selected");
    expect(
      within(bar()).getByRole("button", { name: "Resume (max 5 terminals at once)" }),
    ).toBeDisabled();
  });
});

describe("older than X, then a bulk action", () => {
  it("age filter, header checkbox, Mark done: only the old rows are sent", async () => {
    const spy = await open();
    fireEvent.change(screen.getByLabelText("Age unit"), { target: { value: "h" } });
    fireEvent.change(screen.getByLabelText("Older than"), { target: { value: "2" } });
    fireEvent.click(all());
    expect(selected()).toBe("2 selected");
    fireEvent.click(within(bar()).getByRole("button", { name: "Mark done" }));
    await waitFor(() => {
      expect(postedBodies(spy, "session-mark")).toEqual([
        { ids: ["alpha", "charlie"], mark: "done" },
      ]);
    });
    // Success: refetched, selection cleared, the answer still on screen.
    expect(
      await within(bar()).findByRole("status", { name: /Resumed alpha/u }),
    ).toBeInTheDocument();
    await waitFor(() => {
      expect(sessionCalls(spy)).toBe(2);
    });
    expect(box("alpha")).not.toBeChecked();
    expect(selected()).toBeNull();
    fireEvent.click(within(bar()).getByRole("button", { name: "Dismiss" }));
    expect(screen.queryByRole("region", { name: "Bulk actions" })).toBeNull();
  });

  it("age filter, header checkbox, Delete, confirm", async () => {
    const spy = await open("#/sessions?done=1&older=1w");
    fireEvent.click(all());
    fireEvent.click(within(bar()).getByRole("button", { name: "Delete" }));
    fireEvent.click(within(bar()).getByRole("button", { name: "Confirm delete 2?" }));
    await waitFor(() => {
      expect(postedBodies(spy, "session-delete")).toEqual([
        { ids: ["echo", "foxtrot"] },
      ]);
    });
  });
});
