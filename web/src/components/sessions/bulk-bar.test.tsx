import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  postedBodies,
  REFUSED,
  RESUMED,
  SESSIONS,
  stubSessionsFetch,
} from "../../test/sessions-fixture.ts";
import { BulkBar } from "./bulk-bar.tsx";

const writeText = vi.fn<(text: string) => Promise<void>>(() =>
  Promise.resolve(),
);

const pick = (...ids: string[]) =>
  SESSIONS.sessions.filter((s) => ids.includes(s.id));

function renderBar(ids: string[]): {
  onChanged: () => void;
  onClear: () => void;
} {
  const onChanged = vi.fn();
  const onClear = vi.fn();
  render(<BulkBar onChanged={onChanged} onClear={onClear} selected={pick(...ids)} />);
  return { onChanged, onClear };
}

const bar = (): HTMLElement => screen.getByRole("region", { name: "Bulk actions" });
const click = (name: string): void => {
  fireEvent.click(within(bar()).getByRole("button", { name }));
};

beforeEach(() => {
  writeText.mockReset();
  writeText.mockResolvedValue();
  vi.stubGlobal("navigator", { clipboard: { writeText } });
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("BulkBar", () => {
  it("is absent with nothing selected", () => {
    renderBar([]);
    expect(screen.queryByRole("region", { name: "Bulk actions" })).toBeNull();
  });

  it("marks the selection done, then refetches and clears it", async () => {
    const spy = stubSessionsFetch();
    const { onChanged, onClear } = renderBar(["alpha", "charlie"]);
    expect(bar()).toHaveTextContent("2 selected");
    click("Mark done");
    expect(await within(bar()).findByText(RESUMED.summary)).toBeInTheDocument();
    expect(postedBodies(spy, "session-mark")).toEqual([
      { ids: ["alpha", "charlie"], mark: "done" },
    ]);
    expect(onChanged).toHaveBeenCalledOnce();
    expect(onClear).toHaveBeenCalledOnce();
  });

  it("unmarks the selection", async () => {
    const spy = stubSessionsFetch();
    renderBar(["foxtrot"]);
    click("Unmark");
    await waitFor(() => {
      expect(postedBodies(spy, "session-mark")).toEqual([
        { ids: ["foxtrot"], mark: null },
      ]);
    });
  });

  it("resumes up to five, and refuses to try more", async () => {
    const spy = stubSessionsFetch();
    renderBar(["alpha", "bravo"]);
    click("Resume");
    await waitFor(() => {
      expect(postedBodies(spy, "session-resume")).toEqual([
        { ids: ["alpha", "bravo"] },
      ]);
    });
  });

  it("disables Resume past five, with the reason as its tooltip", () => {
    renderBar(["alpha", "bravo", "charlie", "delta", "echo", "foxtrot"]);
    const resume = within(bar()).getByRole("button", { name: "Resume" });
    expect(resume).toBeDisabled();
    expect(resume).toHaveAttribute("title", "max 5 terminals at once");
  });

  it("deletes only after the in-page confirmation", async () => {
    const spy = stubSessionsFetch();
    renderBar(["echo", "golf"]);
    click("Delete");
    expect(postedBodies(spy, "session-delete")).toEqual([]);
    click("Confirm delete 2?");
    await waitFor(() => {
      expect(postedBodies(spy, "session-delete")).toEqual([
        { ids: ["echo", "golf"] },
      ]);
    });
  });

  it("keeps the selection when the server refuses, and says why", async () => {
    stubSessionsFetch(undefined, REFUSED);
    const { onChanged, onClear } = renderBar(["bravo"]);
    click("Delete");
    click("Confirm delete 1?");
    expect(await within(bar()).findByText(REFUSED.summary)).toBeInTheDocument();
    expect(onClear).not.toHaveBeenCalled();
    expect(onChanged).not.toHaveBeenCalled();
  });

  it("shows a transport failure", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.reject(new Error("offline"))));
    const { onClear } = renderBar(["alpha"]);
    click("Mark done");
    expect(await within(bar()).findByRole("alert")).toHaveTextContent("offline");
    expect(onClear).not.toHaveBeenCalled();
  });

  it("copies every resume command, one per line", async () => {
    renderBar(["alpha", "bravo"]);
    click("Copy commands");
    expect(await within(bar()).findByText("Copied 2 commands")).toBeInTheDocument();
    expect(writeText).toHaveBeenCalledWith(
      "cd '/home/kuhy/src/alpha' && claude --resume alpha\ncd '/home/kuhy/src/bravo' && claude --resume bravo",
    );
  });

  it("says when the clipboard refuses", async () => {
    writeText.mockRejectedValue(new Error("denied"));
    renderBar(["alpha"]);
    click("Copy commands");
    expect(await within(bar()).findByText("Copy failed")).toBeInTheDocument();
  });

  it("clears the selection on request", () => {
    const { onClear } = renderBar(["alpha"]);
    click("Clear selection");
    expect(onClear).toHaveBeenCalledOnce();
  });
});
