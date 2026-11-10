import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { NOW_MS, stubSessionsFetch } from "../../test/sessions-fixture.ts";
import { SessionsPage } from "./sessions-page.tsx";

const now = (): number => NOW_MS;

// Row ids in display order, read off each row's selection checkbox.
function rowIds(): string[] {
  return screen
    .queryAllByRole("checkbox", { name: /^Select (?!all)/ })
    .map((box) => (box.getAttribute("aria-label") ?? "").replace("Select ", ""));
}

async function open(hash = "#/sessions"): Promise<void> {
  globalThis.history.replaceState(null, "", hash);
  stubSessionsFetch();
  render(<SessionsPage now={now} />);
  await screen.findByRole("checkbox", { name: "Select all shown sessions" });
}

// A header paints only a glyph; its sort button carries the column's name.
const header = (name: string): HTMLElement =>
  screen.getByRole("button", { name }).closest("th") as HTMLElement;

// "Project" and "Mark" also name a column's sort button: pick the dropdown.
const select = (name: string): HTMLElement => screen.getByRole("combobox", { name });

beforeEach(() => {
  globalThis.history.replaceState(null, "", "#/sessions");
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("SessionsPage sorting", () => {
  it.each([
    ["Status", "status", "alpha", "golf"],
    ["Age", "age", "delta", "foxtrot"],
    ["Project", "project", "delta", "charlie"],
    ["Title", "title", "charlie", "golf"],
    ["Mark", "mark", "foxtrot", "alpha"],
  ])("cycles %s ascending, descending, off", async (label, key, first, descFirst) => {
    await open("#/sessions?done=1");
    const th = header(label);
    const button = within(th).getByRole("button", { name: label });
    expect(th).toHaveAttribute("aria-sort", "none");
    fireEvent.click(button);
    expect(th).toHaveAttribute("aria-sort", "ascending");
    expect(within(th).getByText("▲")).toBeInTheDocument();
    expect(rowIds()[0]).toBe(first);
    expect(globalThis.location.hash).toBe(`#/sessions?done=1&sort=${key}%3Aasc`);
    fireEvent.click(button);
    expect(th).toHaveAttribute("aria-sort", "descending");
    expect(within(th).getByText("▼")).toBeInTheDocument();
    expect(rowIds()[0]).toBe(descFirst);
    fireEvent.click(button);
    expect(th).toHaveAttribute("aria-sort", "none");
    expect(rowIds()).toEqual([
      "alpha",
      "bravo",
      "charlie",
      "delta",
      "echo",
      "foxtrot",
      "golf",
    ]);
    expect(globalThis.location.hash).toBe("#/sessions?done=1");
  });

  it("shows how each row became done in the Mark column", async () => {
    await open("#/sessions?done=1");
    const cell = (id: string): HTMLElement =>
      screen.getByRole("checkbox", { name: `Select ${id}` }).closest("tr") as HTMLElement;
    expect(within(cell("foxtrot")).getByRole("img", { name: "by hand" })).toHaveTextContent("✋");
    expect(within(cell("echo")).getByRole("img", { name: "by tag" })).toHaveTextContent("🏷");
    expect(within(cell("alpha")).getByRole("img", { name: "not done" })).toHaveTextContent("—");
  });
});

describe("SessionsPage filters", () => {
  it("filters by status chips with counts; a done chip shows its rows", async () => {
    await open();
    const status = screen.getByRole("group", { name: "Status" });
    fireEvent.click(within(status).getByRole("checkbox", { name: /question \(\d+\)/ }));
    fireEvent.click(within(status).getByRole("checkbox", { name: /running \(\d+\)/ }));
    expect(rowIds()).toEqual(["bravo", "delta"]);
    expect(globalThis.location.hash).toBe(
      "#/sessions?status=question&status=running",
    );
    fireEvent.click(within(status).getByRole("checkbox", { name: /done \(\d+\)/ }));
    expect(rowIds()).toEqual(["bravo", "delta", "echo", "foxtrot"]);
    fireEvent.click(within(status).getByRole("checkbox", { name: /question \(\d+\)/ }));
    expect(rowIds()).toEqual(["delta", "echo", "foxtrot"]);
  });

  it("filters by project from a sorted dropdown", async () => {
    await open();
    const project = select("Project");
    expect(
      within(project).getAllByRole("option").map((o) => o.textContent),
    ).toEqual(["∗", "delta", "foxtrot", "golf", "panel", "router"]);
    expect(within(project).getByRole("option", { name: "All projects" })).toHaveValue("");
    fireEvent.change(project, { target: { value: "panel" } });
    expect(rowIds()).toEqual(["alpha", "bravo"]);
    expect(globalThis.location.hash).toBe("#/sessions?project=panel");
    fireEvent.change(project, { target: { value: "" } });
    expect(rowIds()).toHaveLength(4);
  });

  it("filters to rows older than N hours, days or weeks", async () => {
    await open();
    fireEvent.change(screen.getByLabelText("Age unit"), { target: { value: "h" } });
    expect(rowIds()).toHaveLength(4);
    fireEvent.change(screen.getByLabelText("Older than"), { target: { value: "2" } });
    expect(rowIds()).toEqual(["alpha", "charlie"]);
    expect(globalThis.location.hash).toBe("#/sessions?older=2h");
    fireEvent.change(screen.getByLabelText("Age unit"), { target: { value: "w" } });
    expect(rowIds()).toEqual([]);
    expect(screen.getByRole("cell", { name: "No sessions match." })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Older than"), { target: { value: "" } });
    expect(rowIds()).toHaveLength(4);
    expect(globalThis.location.hash).toBe("#/sessions");
  });

  it("filters by mark; a done mark shows done rows without Show done", async () => {
    await open();
    const mark = select("Mark");
    expect(
      within(mark).getAllByRole("option").map((o) => o.getAttribute("aria-label")),
    ).toEqual(["All", "Marked done by hand", "Done by tag", "Not done"]);
    fireEvent.change(mark, { target: { value: "manual" } });
    expect(rowIds()).toEqual(["foxtrot"]);
    fireEvent.change(mark, { target: { value: "tag" } });
    expect(rowIds()).toEqual(["echo", "golf"]);
    fireEvent.change(mark, { target: { value: "open" } });
    expect(rowIds()).toEqual(["alpha", "bravo", "charlie", "delta"]);
    expect(globalThis.location.hash).toBe("#/sessions?mark=open");
    fireEvent.change(mark, { target: { value: "all" } });
    expect(globalThis.location.hash).toBe("#/sessions");
  });

  it("restores every filter and the sort from the hash, combined", async () => {
    await open(
      "#/sessions?status=done&status=continuing&project=panel&older=1d&mark=tag&sort=age:asc",
    );
    expect(rowIds()).toEqual(["echo"]);
    expect(screen.getByRole("checkbox", { name: "done (2)" })).toBeChecked();
    expect(screen.getByRole("checkbox", { name: "continuing (1)" })).toBeChecked();
    expect(screen.getByRole("checkbox", { name: "running (1)" })).not.toBeChecked();
    expect(select("Project")).toHaveValue("panel");
    expect(screen.getByLabelText("Older than")).toHaveValue(1);
    expect(screen.getByLabelText("Age unit")).toHaveValue("d");
    expect(select("Mark")).toHaveValue("tag");
    expect(header("Age")).toHaveAttribute("aria-sort", "ascending");
    fireEvent.change(select("Project"), { target: { value: "" } });
    expect(rowIds()).toEqual(["echo"]);
    fireEvent.change(screen.getByLabelText("Older than"), { target: { value: "" } });
    expect(rowIds()).toEqual(["golf", "echo"]);
  });

  it("keeps a hashed project that vanished, and ignores impossible values", async () => {
    await open("#/sessions?project=gone&mark=tag&older=2d");
    expect(select("Project")).toHaveValue("gone");
    expect(screen.getByRole("cell", { name: "No sessions match." })).toBeInTheDocument();
    fireEvent.change(select("Mark"), { target: { value: "bogus" } });
    fireEvent.change(screen.getByLabelText("Age unit"), { target: { value: "bogus" } });
    // Neither change reached the query: the hash is still the one loaded.
    expect(globalThis.location.hash).toBe(
      "#/sessions?project=gone&mark=tag&older=2d",
    );
    expect(select("Mark")).toHaveValue("tag");
  });
});
