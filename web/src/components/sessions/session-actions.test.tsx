import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { SessionEntry } from "../../lib/sessions-api.ts";

import {
  postedBodies,
  RESUMED,
  SESSIONS,
  stubSessionsFetch,
} from "../../test/sessions-fixture.ts";
import { SessionActions } from "./session-actions.tsx";

const writeText = vi.fn<(text: string) => Promise<void>>(() =>
  Promise.resolve(),
);

function session(id: string): SessionEntry {
  const found = SESSIONS.sessions.find((s) => s.id === id);
  if (found === undefined) throw new Error(`no fixture ${id}`);
  return found;
}

beforeEach(() => {
  writeText.mockReset();
  writeText.mockResolvedValue();
  vi.stubGlobal("navigator", { clipboard: { writeText } });
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("SessionActions", () => {
  it("resumes the session and shows the server's answer", async () => {
    const spy = stubSessionsFetch();
    render(<SessionActions onChanged={vi.fn()} session={session("alpha")} />);
    fireEvent.click(screen.getByRole("button", { name: "Resume alpha" }));
    expect(await screen.findByText(RESUMED.summary)).toBeInTheDocument();
    expect(postedBodies(spy, "session-resume")).toEqual([{ id: "alpha" }]);
  });

  it("copies the resume command", async () => {
    render(<SessionActions onChanged={vi.fn()} session={session("bravo")} />);
    fireEvent.click(screen.getByRole("button", { name: "Copy resume command for bravo" }));
    expect(await screen.findByText("Copied")).toBeInTheDocument();
    expect(writeText).toHaveBeenCalledWith(
      "cd '/home/kuhy/src/bravo' && claude --resume bravo",
    );
  });

  it("says when the clipboard refuses", async () => {
    writeText.mockRejectedValue(new Error("denied"));
    render(<SessionActions onChanged={vi.fn()} session={session("bravo")} />);
    fireEvent.click(screen.getByRole("button", { name: "Copy resume command for bravo" }));
    expect(await screen.findByText("Copy failed")).toBeInTheDocument();
  });

  it("marks done, then asks for a refetch", async () => {
    const spy = stubSessionsFetch();
    const onChanged = vi.fn();
    render(<SessionActions onChanged={onChanged} session={session("charlie")} />);
    fireEvent.click(screen.getByRole("button", { name: "Mark charlie done" }));
    await waitFor(() => {
      expect(onChanged).toHaveBeenCalledOnce();
    });
    expect(postedBodies(spy, "session-mark")).toEqual([
      { id: "charlie", mark: "done" },
    ]);
  });

  it("unmarks only a manual mark; a tag-done row has nothing to undo", async () => {
    const spy = stubSessionsFetch();
    const onChanged = vi.fn();
    const { unmount } = render(
      <SessionActions onChanged={onChanged} session={session("foxtrot")} />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Unmark foxtrot" }));
    await waitFor(() => {
      expect(onChanged).toHaveBeenCalledOnce();
    });
    expect(postedBodies(spy, "session-mark")).toEqual([
      { id: "foxtrot", mark: null },
    ]);
    unmount();
    render(<SessionActions onChanged={onChanged} session={session("echo")} />);
    expect(screen.queryByRole("button", { name: /mark/i })).toBeNull();
  });

  it("shows a transport failure instead of swallowing it", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.reject(new Error("offline"))));
    const onChanged = vi.fn();
    render(<SessionActions onChanged={onChanged} session={session("alpha")} />);
    fireEvent.click(screen.getByRole("button", { name: "Mark alpha done" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("offline");
    expect(onChanged).not.toHaveBeenCalled();
  });
});
