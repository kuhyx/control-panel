import { describe, expect, it } from "vitest";

import {
  decodeSort,
  describeTable,
  EMPTY_TABLE,
  panelParameters as panelParameters,
  readTable,
  toggleSort,
  writeTable,
} from "./table-parameters.ts";

describe("table params", () => {
  it("round-trips a table's state through the hash keys", () => {
    const state = {
      filters: { kind: "=a|b", usd: "1..2" },
      limit: 0,
      q: "x",
      sort: [
        { desc: true, key: "usd" },
        { desc: false, key: "name" },
      ],
    };
    const parameters = writeTable(
      { "t.p/other.q": "keep", "t.p/rows.q": "old" },
      "p/rows",
      state,
    );
    expect(parameters).toEqual({
      "t.p/other.q": "keep",
      "t.p/rows.f.kind": "=a|b",
      "t.p/rows.f.usd": "1..2",
      "t.p/rows.limit": "0",
      "t.p/rows.q": "x",
      "t.p/rows.sort": "-usd,name",
    });
    expect(readTable(parameters, "p/rows")).toEqual(state);
    expect(writeTable(parameters, "p/rows", EMPTY_TABLE)).toEqual({
      "t.p/other.q": "keep",
    });
  });

  it("ignores a malformed limit and empty sort keys", () => {
    expect(readTable({ "t.r.limit": "x" }, "r").limit).toBeNull();
    expect(decodeSort("-,,a")).toEqual([{ desc: false, key: "a" }]);
  });

  it("re-keys one panel's params for its API call", () => {
    expect(
      panelParameters(
        { "t.a/rows.q": "1", "t.ab/x.q": "3", "t.b/rows.q": "2" },
        "a",
      ),
    ).toEqual({
      "t.rows.q": "1",
    });
  });

  it("toggles a lead key, replaces by click and appends by shift-click", () => {
    const lead = [{ desc: true, key: "usd" }];
    expect(toggleSort([], "usd", false)).toEqual(lead);
    expect(toggleSort(lead, "usd", false)).toEqual([
      { desc: false, key: "usd" },
    ]);
    expect(toggleSort(lead, "n", false)).toEqual([{ desc: true, key: "n" }]);
    const two = toggleSort(lead, "n", true);
    expect(two).toEqual([...lead, { desc: true, key: "n" }]);
    expect(toggleSort(two, "n", true)).toEqual([
      ...lead,
      { desc: false, key: "n" },
    ]);
  });

  it("describes a state for the copied header", () => {
    expect(describeTable(EMPTY_TABLE)).toBe("none");
    expect(
      describeTable({
        filters: { n: "1.." },
        limit: null,
        q: "z",
        sort: [{ desc: true, key: "n" }],
      }),
    ).toBe('search "z", n 1.., sort -n');
  });
});
