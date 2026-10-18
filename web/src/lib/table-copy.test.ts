import { describe, expect, it } from "vitest";

import {
  asJson,
  describeFilters,
  forClaude,
  markdownTable,
} from "./table-copy.ts";
import { EMPTY_TABLE } from "./table-parameters.ts";
import { EMPTY_QUERY } from "./tokens-api.ts";

const COLUMNS = [
  { key: "name", label: "name" },
  { key: "usd", label: "USD", unit: "USD" },
];

const CONTEXT = {
  matched: null,
  query: null,
  selected: true,
  state: EMPTY_TABLE,
  title: "t",
  view: "v",
  window: null,
};

describe("table copy", () => {
  it("writes a compact markdown table", () => {
    const rows = [
      { name: "a|b\n c", usd: 1.234567 },
      { name: { x: 1 }, usd: 3 },
      { name: null, usd: undefined },
    ];
    expect(markdownTable(COLUMNS, rows)).toBe(
      [
        "| name | USD |",
        "|---|---|",
        String.raw`| a\|b c | 1.235 |`,
        '| {"x":1} | 3 |',
        "| — | — |",
      ].join("\n"),
    );
  });

  it("heads it with the selection, and units as labelled when none are given", () => {
    const text = forClaude(
      [{ key: "name", label: "name" }],
      [{ name: "a" }],
      CONTEXT,
    );
    expect(text.split("\n", 1)[0]).toBe(
      "View: v / t · window n/a · filters: none · table: none · 1 selected rows · units: as labelled; USD = API list price",
    );
    const json = JSON.parse(
      asJson(COLUMNS, [{ name: "a" }], { ...CONTEXT, selected: false }),
    ) as {
      header: string;
    };
    expect(json.header).toContain("1 of 1 matching rows");
  });

  it("lists only the filters that are set", () => {
    expect(describeFilters(EMPTY_QUERY)).toBe("none");
    expect(
      describeFilters({
        ...EMPTY_QUERY,
        model: "m",
        scope: "sub",
        to: "2026-01-01",
      }),
    ).toBe("model=m, to=2026-01-01, scope=sub");
  });
});
