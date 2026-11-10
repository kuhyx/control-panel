import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";

import type { ColumnSpec } from "../lib/table-state.ts";

import { useTableView } from "../lib/table-state.ts";
import { ColumnHeader, NoMatchRow, TableHint } from "./table-controls.tsx";

interface Row {
  kind: string;
  name: string;
}

const ROWS: Row[] = [
  { kind: "timer", name: "alpha" },
  { kind: "service", name: "Bravo" },
  { kind: "timer", name: "charlie" },
];

const COLUMNS: ColumnSpec<Row>[] = [
  { glyph: "#", id: "name", label: "Name", search: true, text: (r) => r.name },
  { filter: true, glyph: "◆", id: "kind", label: "Kind", text: (r) => r.kind },
];

function Harness(): React.JSX.Element {
  const view = useTableView("t", COLUMNS, ROWS);
  return (
    <>
      <TableHint view={view} />
      <table>
        <thead>
          <tr>
            {COLUMNS.map((column) => {
              return (
                <ColumnHeader column={column} key={column.id} view={view} />
              );
            })}
            <th scope="col">Actions</th>
          </tr>
        </thead>
        <tbody>
          {view.rows.length === 0 && <NoMatchRow colSpan={3} />}
          {view.rows.map((row) => {
            return (
            <tr key={row.name}>
              <th scope="row">{row.name}</th>
              <td>{row.kind}</td>
              <td />
            </tr>
            );
          })}
        </tbody>
      </table>
    </>
  );
}

const rowNames = (): string[] =>
  screen.getAllByRole("rowheader").map((cell) => cell.textContent);

beforeEach(() => {
  globalThis.history.replaceState(null, "", "#");
});

describe("ColumnHeader", () => {
  it("cycles sort ascending, descending, off with aria-sort", async () => {
    const user = userEvent.setup();
    render(<Harness />);
    const button = screen.getByRole("button", { name: "Name" });
    const header = button.closest("th");
    expect(header).toHaveAttribute("aria-sort", "none");
    await user.click(button);
    expect(header).toHaveAttribute("aria-sort", "ascending");
    expect(rowNames()).toEqual(["alpha", "Bravo", "charlie"]);
    await user.click(button);
    expect(header).toHaveAttribute("aria-sort", "descending");
    expect(rowNames()).toEqual(["charlie", "Bravo", "alpha"]);
    await user.click(button);
    expect(header).toHaveAttribute("aria-sort", "none");
    expect(globalThis.location.hash).toBe("");
  });

  it("gives Actions no controls", () => {
    render(<Harness />);
    const actions = screen.getByRole("columnheader", { name: "Actions" });
    expect(actions).not.toHaveAttribute("aria-sort");
    expect(within(actions).queryByRole("button")).not.toBeInTheDocument();
  });

  it("searches a column case-insensitively and puts it in the hash", async () => {
    const user = userEvent.setup();
    render(<Harness />);
    await user.type(screen.getByLabelText("Search Name"), "BRA");
    expect(rowNames()).toEqual(["Bravo"]);
    expect(globalThis.location.hash).toBe("#?t.q.name=BRA");
    expect(screen.getByRole("status", { name: "1 of 3 shown" })).toHaveTextContent("1/3");
  });

  it("paints the column glyph and speaks the label", () => {
    render(<Harness />);
    const button = screen.getByRole("button", { name: "Name" });
    expect(button).toHaveTextContent("#");
    expect(button).not.toHaveTextContent("Name");
  });

  it("offers a multi-select over the distinct values", async () => {
    const user = userEvent.setup();
    render(<Harness />);
    expect(screen.getAllByRole("checkbox").map((box) => box.parentElement?.textContent)).toEqual([
      "service",
      "timer",
    ]);
    await user.click(screen.getByRole("checkbox", { name: "timer" }));
    expect(rowNames()).toEqual(["alpha", "charlie"]);
    await user.click(screen.getByRole("checkbox", { name: "service" }));
    expect(rowNames()).toHaveLength(3);
    expect(screen.getByLabelText("Filter Kind")).toHaveTextContent("▾ 2");
    await user.click(screen.getByRole("checkbox", { name: "timer" }));
    expect(rowNames()).toEqual(["Bravo"]);
  });

  it("shows a bare caret while nothing is picked", () => {
    render(<Harness />);
    expect(screen.getByLabelText("Filter Kind")).toHaveTextContent(/^▾$/u);
  });

  it("paints filter options as glyphs when the column maps them", () => {
    const glyphed: ColumnSpec<Row> = {
      filter: true,
      glyph: "◆",
      id: "kind",
      label: "Kind",
      optionGlyph: (value) => (value === "timer" ? "⏱" : "⚙"),
      text: (r) => r.kind,
    };
    function Glyphed(): React.JSX.Element {
      const view = useTableView("g", [glyphed], ROWS);
      return (
        <table>
          <thead>
            <tr>
              <ColumnHeader column={glyphed} view={view} />
            </tr>
          </thead>
        </table>
      );
    }
    render(<Glyphed />);
    const group = screen.getByRole("group", { name: "Kind values" });
    expect(within(group).getByRole("img", { name: "timer" })).toHaveTextContent("⏱");
    expect(within(group).getByRole("img", { name: "service" })).toHaveTextContent("⚙");
    expect(within(group).queryByText("timer")).not.toBeInTheDocument();
  });

  it("labels an empty value so it can still be unticked", async () => {
    // A selected value that no row has any more stays listed; "" has no text.
    globalThis.history.replaceState(null, "", "#?t.f.kind=");
    const user = userEvent.setup();
    render(<Harness />);
    const box = screen.getByRole("checkbox", { name: "(empty)" });
    expect(box).toBeChecked();
    expect(screen.queryAllByRole("rowheader")).toHaveLength(0);
    await user.click(box);
    expect(rowNames()).toHaveLength(3);
  });

  it("restores state from the hash on first render", () => {
    globalThis.history.replaceState(null, "", "#?t.f.kind=timer&t.sort=name:desc");
    render(<Harness />);
    expect(rowNames()).toEqual(["charlie", "alpha"]);
    expect(screen.getByRole("checkbox", { name: "timer" })).toBeChecked();
  });
});

describe("TableHint", () => {
  it("is absent until something filters, then offers a clear button", async () => {
    const user = userEvent.setup();
    render(<Harness />);
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
    await user.type(screen.getByLabelText("Search Name"), "zzz");
    expect(screen.getByRole("status", { name: "0 of 3 shown" })).toHaveTextContent("0/3");
    expect(
      screen.getByRole("cell", { name: "No rows match the current filters." }),
    ).toHaveTextContent("∅");
    await user.click(screen.getByRole("button", { name: "Clear filters" }));
    expect(rowNames()).toHaveLength(3);
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Search Name")).toHaveValue("");
  });
});
