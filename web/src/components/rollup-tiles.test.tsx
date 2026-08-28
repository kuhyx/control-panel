import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { RollupTiles } from "./rollup-tiles.tsx";

describe("RollupTiles", () => {
  it("shows only the states that occur", () => {
    render(<RollupTiles rollup={{ ARMED: 38, UNARMED: 3 }} />);
    const list = screen.getByRole("list", { name: "Fleet summary" });
    const items = within(list).getAllByRole("listitem");
    expect(items).toHaveLength(2);
    expect(items[0]).toHaveTextContent("38");
    expect(items[0]).toHaveTextContent("ARMED");
  });

  it("hides zero counts rather than rendering an empty tile", () => {
    render(<RollupTiles rollup={{ ARMED: 1, BAD: 0 }} />);
    expect(screen.queryByText("BAD")).not.toBeInTheDocument();
  });

  it("renders nothing when the fleet is empty", () => {
    render(<RollupTiles rollup={{}} />);
    expect(
      within(screen.getByRole("list")).queryAllByRole("listitem"),
    ).toHaveLength(0);
  });
});
