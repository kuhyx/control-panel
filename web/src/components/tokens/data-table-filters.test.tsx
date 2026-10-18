import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { lastTables, querySpy, scoped } from "../../test/table-fixture.tsx";
import { COMMIT_MS } from "./draft-input.tsx";

afterEach(() => {
  vi.useRealTimers();
});

describe("DataTable state in the hash", () => {
  it("keeps sort, filters, search and limit in the URL hash", () => {
    vi.useFakeTimers();
    const onQuery = querySpy();
    render(scoped(onQuery, { "t.demo/rows.sort": "-n" }));
    const last = (): Record<string, string> => lastTables(onQuery);
    expect(screen.getByRole("columnheader", { name: "n ▼" })).toHaveAttribute(
      "aria-sort",
      "descending",
    );
    fireEvent.click(screen.getByRole("button", { name: "n ▼" }));
    expect(last()).toEqual({ "t.demo/rows.sort": "n" });
    fireEvent.click(screen.getByRole("button", { name: "label" }), {
      shiftKey: true,
    });
    expect(last()).toEqual({ "t.demo/rows.sort": "-n,-label" });
    fireEvent.change(screen.getByLabelText("search this table"), {
      target: { value: "al" },
    });
    act(() => {
      vi.advanceTimersByTime(COMMIT_MS);
    });
    expect(last()).toEqual({ "t.demo/rows.q": "al", "t.demo/rows.sort": "-n" });
    fireEvent.click(screen.getByRole("button", { name: "Show all" }));
    expect(last()["t.demo/rows.limit"]).toBe("0");
  });

  it("filters by contains, numeric range and enum membership", () => {
    vi.useFakeTimers();
    const onQuery = querySpy();
    render(
      scoped(onQuery, {
        "t.demo/rows.f.kind": "=tool",
        "t.demo/rows.f.n": "1..9",
      }),
    );
    const last = (): Record<string, string> => lastTables(onQuery);
    expect(screen.getByLabelText("n min")).toHaveValue("1");
    fireEvent.change(screen.getByLabelText("n max"), { target: { value: "" } });
    act(() => {
      vi.advanceTimersByTime(COMMIT_MS);
    });
    expect(last()["t.demo/rows.f.n"]).toBe("1..");
    fireEvent.change(screen.getByLabelText("n min"), { target: { value: "" } });
    act(() => {
      vi.advanceTimersByTime(COMMIT_MS);
    });
    fireEvent.change(screen.getByLabelText("label contains"), {
      target: { value: "x" },
    });
    act(() => {
      vi.advanceTimersByTime(COMMIT_MS);
    });
    expect(last()["t.demo/rows.f.label"]).toBe("~x");
    const kinds = screen.getByLabelText("kind is one of");
    const [mark, tool] =
      within(kinds).getAllByRole<HTMLOptionElement>("option");
    if (mark === undefined || tool === undefined) throw new Error("no options");
    mark.selected = true;
    fireEvent.change(kinds);
    expect(last()["t.demo/rows.f.kind"]).toBe("=mark|tool");
    mark.selected = false;
    tool.selected = false;
    fireEvent.change(kinds);
    expect(last()["t.demo/rows.f.kind"]).toBeUndefined();
  });

  it("shows multi-key arrows, odd filter rules and resyncs drafts from the hash", () => {
    const onQuery = querySpy();
    const odd = {
      "t.demo/rows.f.label": "=x",
      "t.demo/rows.f.n": "7",
      "t.demo/rows.sort": "n,-label",
    };
    const { rerender } = render(scoped(onQuery, odd));
    expect(screen.getByRole("columnheader", { name: "n ▲1" })).toHaveAttribute(
      "aria-sort",
      "ascending",
    );
    expect(
      screen.getByRole("columnheader", { name: "label ▼2" }),
    ).toHaveAttribute("aria-sort", "none");
    expect(screen.getByLabelText("n min")).toHaveValue("");
    expect(screen.getByLabelText("label contains")).toHaveValue("");
    vi.useFakeTimers();
    const last = (): Record<string, string> => lastTables(onQuery);
    for (const [field, value, key, rule] of [
      ["n max", "3", "t.demo/rows.f.n", "..3"],
      ["label contains", "q", "t.demo/rows.f.label", "~q"],
    ] as const) {
      fireEvent.change(screen.getByLabelText(field), { target: { value } });
      act(() => {
        vi.advanceTimersByTime(COMMIT_MS);
      });
      expect(last()[key]).toBe(rule);
    }
    rerender(
      scoped(onQuery, {
        ...odd,
        "t.demo/rows.f.label": "~q",
        "t.demo/rows.f.n": "..3",
      }),
    );
    for (const [field, key] of [
      ["label contains", "t.demo/rows.f.label"],
      ["n max", "t.demo/rows.f.n"],
    ] as const) {
      fireEvent.change(screen.getByLabelText(field), { target: { value: "" } });
      act(() => {
        vi.advanceTimersByTime(COMMIT_MS);
      });
      expect(last()[key]).toBeUndefined();
    }
    vi.useRealTimers();
    rerender(scoped(onQuery, { ...odd, "t.demo/rows.q": "fresh" }));
    expect(screen.getByLabelText("search this table")).toHaveValue("fresh");
  });
});
