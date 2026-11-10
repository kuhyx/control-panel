import { act, renderHook, waitFor } from "@testing-library/react";
import { createElement } from "react";
import { renderToString } from "react-dom/server";
import { beforeEach, describe, expect, it } from "vitest";

import type { ColumnSpec } from "./table-state.ts";

import { applyTableState, filterOptions, nextSort } from "./table-query.ts";
import {
  EMPTY_STATE,
  readTableState,
  useTableView,
  writeTableState,
} from "./table-state.ts";

interface Row {
  at: null | number;
  kind: string;
  name: string;
}

const ROWS: Row[] = [
  { at: 30, kind: "b", name: "Alpha" },
  { at: null, kind: "a", name: "bravo" },
  { at: 10, kind: "a", name: "Charlie" },
];

const COLUMNS: ColumnSpec<Row>[] = [
  { glyph: "#", id: "name", label: "Name", search: true, text: (r) => r.name },
  { filter: true, glyph: "◆", id: "kind", label: "Kind", text: (r) => r.kind },
  { glyph: "⏱", id: "at", label: "At", sortKey: (r) => r.at, text: (r) => String(r.at) },
];
const IDS = COLUMNS.map((c) => c.id);

const names = (rows: Row[]): string[] => rows.map((r) => r.name);

beforeEach(() => {
  globalThis.history.replaceState(null, "", "#");
});

describe("hash round trip", () => {
  it("writes and reads sort, search and filters, namespaced", () => {
    const state = {
      filters: { kind: ["a", "x y"] },
      search: { name: "br&vo" },
      sort: { column: "at", direction: "desc" as const },
    };
    const hash = writeTableState("#/s/hosts", "units", state);
    expect(hash).toBe(
      "#/s/hosts?units.sort=at:desc&units.q.name=br%26vo&units.f.kind=a&units.f.kind=x%20y",
    );
    expect(readTableState(hash, "units", IDS)).toEqual(state);
    // Another table's namespace sees none of it.
    expect(readTableState(hash, "containers", IDS)).toEqual(EMPTY_STATE);
  });

  it("keeps other tables' params and the path when rewriting one", () => {
    const first = writeTableState("#/s/x", "units", {
      ...EMPTY_STATE,
      sort: { column: "name", direction: "asc" },
    });
    const both = writeTableState(first, "containers", {
      ...EMPTY_STATE,
      search: { name: "q" },
    });
    expect(both).toBe("#/s/x?units.sort=name:asc&containers.q.name=q");
    expect(writeTableState(both, "units", EMPTY_STATE)).toBe("#/s/x?containers.q.name=q");
    expect(writeTableState("#/s/x?units.q.name=a", "units", EMPTY_STATE)).toBe("#/s/x");
  });

  it("drops blank search text instead of writing an empty param", () => {
    expect(
      writeTableState("#/s/x", "t", { ...EMPTY_STATE, search: { name: "" } }),
    ).toBe("#/s/x");
  });

  it("works on an empty hash (overview)", () => {
    expect(
      writeTableState("", "fleet", { ...EMPTY_STATE, search: { name: "a" } }),
    ).toBe("#?fleet.q.name=a");
  });

  it("ignores unknown columns and malformed sort", () => {
    expect(readTableState("#?t.sort=nope:asc&t.q.nope=a", "t", IDS)).toEqual(EMPTY_STATE);
    expect(readTableState("#?t.sort=name:sideways", "t", IDS)).toEqual(EMPTY_STATE);
    expect(readTableState("#?t.sort=name", "t", IDS)).toEqual(EMPTY_STATE);
  });
});

describe("applyTableState", () => {
  it("searches case-insensitively and trims", () => {
    const state = { ...EMPTY_STATE, search: { name: "  BRAV " } };
    expect(names(applyTableState(ROWS, COLUMNS, state))).toEqual(["bravo"]);
  });

  it("ANDs columns and ORs the values within one filter", () => {
    const either = { ...EMPTY_STATE, filters: { kind: ["a", "b"] } };
    expect(applyTableState(ROWS, COLUMNS, either)).toHaveLength(3);
    const both = { ...either, search: { name: "a" } };
    expect(names(applyTableState(ROWS, COLUMNS, both))).toEqual(["Alpha", "bravo", "Charlie"]);
    const narrow = { ...EMPTY_STATE, filters: { kind: ["a"] }, search: { name: "char" } };
    expect(names(applyTableState(ROWS, COLUMNS, narrow))).toEqual(["Charlie"]);
  });

  it("sorts text case-insensitively by locale and numbers numerically", () => {
    const byName = { ...EMPTY_STATE, sort: { column: "name", direction: "asc" as const } };
    expect(names(applyTableState(ROWS, COLUMNS, byName))).toEqual(["Alpha", "bravo", "Charlie"]);
    const byAt = { ...EMPTY_STATE, sort: { column: "at", direction: "asc" as const } };
    expect(names(applyTableState(ROWS, COLUMNS, byAt))).toEqual(["Charlie", "Alpha", "bravo"]);
  });

  it("puts null keys last in both directions", () => {
    const desc = { ...EMPTY_STATE, sort: { column: "at", direction: "desc" as const } };
    expect(names(applyTableState(ROWS, COLUMNS, desc))).toEqual(["Alpha", "Charlie", "bravo"]);
  });

  it("keeps ties, including several nulls, in the caller's order", () => {
    const rows: Row[] = [
      { at: null, kind: "a", name: "first" },
      { at: 5, kind: "a", name: "mid" },
      { at: null, kind: "a", name: "second" },
    ];
    for (const direction of ["asc", "desc"] as const) {
      const state = { ...EMPTY_STATE, sort: { column: "at", direction } };
      const sorted = names(applyTableState(rows, COLUMNS, state));
      expect(sorted).toEqual(["mid", "first", "second"]);
    }
  });

  it("keeps the caller's order with no sort", () => {
    expect(names(applyTableState(ROWS, COLUMNS, EMPTY_STATE))).toEqual([
      "Alpha",
      "bravo",
      "Charlie",
    ]);
  });
});

describe("filterOptions", () => {
  it("lists distinct values in sort order and keeps selected ones that vanished", () => {
    const [, kind] = COLUMNS;
    expect(filterOptions(ROWS, kind!, [])).toEqual(["a", "b"]);
    expect(filterOptions(ROWS, kind!, ["gone"])).toEqual(["a", "b", "gone"]);
  });
});

describe("nextSort", () => {
  it("cycles ascending, descending, off", () => {
    const asc = nextSort(null, "name");
    expect(asc).toEqual({ column: "name", direction: "asc" });
    const desc = nextSort(asc, "name");
    expect(desc).toEqual({ column: "name", direction: "desc" });
    expect(nextSort(desc, "name")).toBeNull();
    expect(nextSort(desc, "kind")).toEqual({ column: "kind", direction: "asc" });
  });
});

describe("useTableView", () => {
  it("writes to the hash without a history entry and re-renders", () => {
    const before = globalThis.history.length;
    const { result } = renderHook(() => useTableView("t", COLUMNS, ROWS));
    expect(result.current.filtered).toBe(false);
    act(() => {
      result.current.setSearch("name", "al");
    });
    expect(globalThis.location.hash).toBe("#?t.q.name=al");
    expect(globalThis.history).toHaveLength(before);
    expect(names(result.current.rows)).toEqual(["Alpha"]);
    expect(result.current.filtered).toBe(true);
    expect(result.current.total).toBe(3);
  });

  it("reads state already in the hash (reload) and reacts to hashchange", async () => {
    globalThis.history.replaceState(null, "", "#?t.f.kind=b");
    const { result } = renderHook(() => useTableView("t", COLUMNS, ROWS));
    expect(names(result.current.rows)).toEqual(["Alpha"]);
    act(() => {
      globalThis.location.hash = "#?t.f.kind=a";
    });
    // jsdom delivers hashchange asynchronously.
    await waitFor(() => {
      expect(names(result.current.rows)).toEqual(["bravo", "Charlie"]);
    });
  });

  it("toggles sort, sets filters, and clear keeps the sort", () => {
    const { result } = renderHook(() => useTableView("t", COLUMNS, ROWS));
    act(() => {
      result.current.toggleSort("name");
    });
    act(() => {
      result.current.setFilter("kind", ["a"]);
    });
    expect(globalThis.location.hash).toBe("#?t.sort=name:asc&t.f.kind=a");
    act(() => {
      result.current.clear();
    });
    expect(globalThis.location.hash).toBe("#?t.sort=name:asc");
    act(() => {
      result.current.toggleSort("name");
      result.current.toggleSort("name");
    });
    expect(globalThis.location.hash).toBe("");
  });

  it("renders server-side from an empty hash, ignoring the browser's", () => {
    globalThis.history.replaceState(null, "", "#?t.sort=name:asc");
    function Probe(): React.JSX.Element {
      const view = useTableView("t", COLUMNS, ROWS);
      return createElement("span", null, `${view.state.sort?.column ?? "none"}:${names(view.rows).join(",")}`);
    }
    expect(renderToString(createElement(Probe))).toBe("<span>none:Alpha,bravo,Charlie</span>");
  });

  it("keeps two tables on one page independent", () => {
    const first = renderHook(() => useTableView("one", COLUMNS, ROWS));
    const second = renderHook(() => useTableView("two", COLUMNS, ROWS));
    act(() => {
      first.result.current.setSearch("name", "a");
    });
    act(() => {
      second.result.current.toggleSort("at");
    });
    expect(globalThis.location.hash).toBe("#?one.q.name=a&two.sort=at:asc");
    expect(second.result.current.filtered).toBe(false);
  });
});
