import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  NOW_MS,
  postedBodies,
  SESSIONS,
  stubSessionsFetch,
} from "../../test/sessions-fixture.ts";
import { SessionsPage } from "./sessions-page.tsx";

const now = (): number => NOW_MS;

function rowIds(): string[] {
  return screen
    .getAllByRole("button", { name: /^title of|^Fix the Router/ })
    .map((button) => button.textContent);
}

beforeEach(() => {
  globalThis.history.replaceState(null, "", "#/sessions");
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("SessionsPage", () => {
  it("reads, then counts every status and the scan", async () => {
    stubSessionsFetch();
    render(<SessionsPage now={now} />);
    expect(screen.getByText("Reading…")).toBeInTheDocument();
    expect(
      await screen.findByText(
        /1 need action · 1 question · 1 untagged · 1 running · 2 done · 1 continuing/,
      ),
    ).toHaveTextContent("1033 sessions scanned in 840 ms");
    expect(
      screen.getByRole("heading", { name: "Claude Code sessions" }),
    ).toBeInTheDocument();
  });

  it("hides done rows until Show done is ticked, and keeps it in the hash", async () => {
    stubSessionsFetch();
    render(<SessionsPage now={now} />);
    await screen.findByText("title of alpha");
    expect(rowIds()).toEqual([
      "title of alpha",
      "title of bravo",
      "Fix the Router",
      "title of delta",
    ]);
    const alpha = screen.getByText("title of alpha").closest("tr");
    expect(alpha).not.toHaveClass("dim");
    expect(within(alpha as HTMLElement).getByText("needs action")).toHaveClass(
      "badge",
    );
    expect(within(alpha as HTMLElement).getByText("3 h ago")).toBeVisible();
    fireEvent.click(screen.getByLabelText("Show done"));
    expect(rowIds()).toHaveLength(7);
    expect(screen.getByText("title of golf").closest("tr")).toHaveClass("dim");
    expect(globalThis.location.hash).toBe("#/sessions?done=1");
    fireEvent.click(screen.getByLabelText("Show done"));
    expect(rowIds()).toHaveLength(4);
    expect(globalThis.location.hash).toBe("#/sessions");
  });

  it("narrows rows by the filter and restores it from the hash", async () => {
    globalThis.history.replaceState(null, "", "#/sessions?q=golf&done=1");
    stubSessionsFetch();
    render(<SessionsPage now={now} />);
    expect(await screen.findByText("title of golf")).toBeInTheDocument();
    expect(rowIds()).toEqual(["title of golf"]);
    expect(screen.getByLabelText("Show done")).toBeChecked();
    fireEvent.change(screen.getByLabelText("Filter sessions"), {
      target: { value: "ROUTER" },
    });
    expect(rowIds()).toEqual(["Fix the Router"]);
    expect(globalThis.location.hash).toBe("#/sessions?done=1&q=ROUTER");
    fireEvent.change(screen.getByLabelText("Filter sessions"), {
      target: { value: "nothing-matches" },
    });
    expect(screen.getByText("No sessions match.")).toBeInTheDocument();
  });

  it("expands a row into its last messages, and keeps it open across a refetch", async () => {
    const spy = stubSessionsFetch();
    render(<SessionsPage now={now} />);
    const toggle = await screen.findByRole("button", { name: "title of alpha" });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByText("user asks alpha")).toBeNull();
    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText("user asks alpha")).toBeInTheDocument();
    // The assistant text goes through the markdown renderer.
    expect(screen.getByText("the thing").tagName).toBe("STRONG");
    expect(screen.getByText("/home/kuhy/src/alpha")).toBeInTheDocument();
    expect(screen.getByText("alpha", { selector: "code" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Mark alpha done" }));
    await waitFor(() => {
      expect(postedBodies(spy, "session-mark")).toEqual([
        { ids: ["alpha"], mark: "done" },
      ]);
    });
    await waitFor(() => {
      expect(
        spy.mock.calls.filter(([path]) => path === "/api/sessions"),
      ).toHaveLength(2);
    });
    expect(screen.getByText("user asks alpha")).toBeInTheDocument();
    fireEvent.click(toggle);
    expect(screen.queryByText("user asks alpha")).toBeNull();
  });

  it("names an untitled session instead of leaving an empty button", async () => {
    const [first] = SESSIONS.sessions;
    stubSessionsFetch({ ...SESSIONS, sessions: first ? [{ ...first, title: "" }] : [] });
    render(<SessionsPage now={now} />);
    expect(
      await screen.findByRole("button", { name: "(untitled)" }),
    ).toBeInTheDocument();
  });

  it("shows a failed read as an alert", async () => {
    stubSessionsFetch(null);
    render(<SessionsPage now={now} />);
    expect(await screen.findByRole("alert")).toHaveTextContent("500");
  });
});
