import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { INDEX } from "../../../test/tokens-fixture.ts";
import { view } from "../panels/export-view.tsx";

const DATA = {
  calls: [
    { carry_usd: 0.25, key: "s1", name: "Bash", ts: 1_760_000_000, wall_s: 3 },
  ],
  caption: "Raw rows.",
  marks: [],
  turns: [{ key: "s1", model: "opus", ts: 1_760_000_000, usd: 1.5 }],
};

describe("ExportPanel", () => {
  it("lists the raw rows of every table with their units", () => {
    render(view.render(DATA, { index: INDEX }));
    expect(screen.getByText("Raw rows.")).toBeInTheDocument();
    const [turns, calls] = screen.getAllByRole("table");
    if (turns === undefined || calls === undefined) throw new Error("tables");
    expect(within(turns).getByText("1.5")).toHaveClass("num");
    expect(within(calls).getByText("Bash")).toBeInTheDocument();
    expect(within(calls).queryAllByText(/^1,760/)).toHaveLength(0);
    expect(screen.getByText("No rows match.")).toBeInTheDocument();
    expect(view.order).toBe(99);
  });
});
