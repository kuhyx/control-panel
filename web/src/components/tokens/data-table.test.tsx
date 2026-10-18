import {
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  META,
  type Row,
  ROWS,
  scoped,
  table,
} from "../../test/table-fixture.tsx";
import { DataTable } from "./data-table.tsx";

const writeText = vi.fn<(text: string) => Promise<void>>(() =>
  Promise.resolve(),
);

beforeEach(() => {
  writeText.mockReset();
  writeText.mockResolvedValue();
  vi.stubGlobal("navigator", { clipboard: { writeText } });
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("DataTable", () => {
  it("renders raw and formatted cells, counts and a CSV of every column", () => {
    render(table());
    const body = within(screen.getByRole("table"));
    expect(body.getByText("1,234")).toHaveClass("num");
    expect(body.getByText("—")).toBeInTheDocument();
    expect(body.getByText("#2")).toBeInTheDocument();
    expect(
      screen.getByText("2 shown of 5 matching (9 total)"),
    ).toBeInTheDocument();
    const csv = screen.getByRole("link", { name: "CSV" });
    expect(csv).toHaveAttribute("download", "rows.csv");
    expect(decodeURIComponent(csv.getAttribute("href") ?? "")).toContain(
      'label,n,kind,obj\nalpha,1234,tool,"{""a"":1}"',
    );
  });

  it("selects rows, and copies the selection or every shown row", async () => {
    render(table());
    fireEvent.click(screen.getByRole("button", { name: "Copy for Claude" }));
    await screen.findByText("Copy for Claude: copied");
    expect(writeText.mock.calls[0]?.[0]).toMatch(
      /^View: rows \/ Things · window n\/a/,
    );
    fireEvent.click(screen.getByLabelText("select 5"));
    expect(screen.getByText("picked 1")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Copy as JSON" }));
    await screen.findByText("Copy as JSON: copied");
    const copied = JSON.parse(String(writeText.mock.calls[1]?.[0])) as {
      rows: Row[];
    };
    expect(copied.rows.map((r) => r.n)).toEqual([5]);
    fireEvent.click(screen.getByLabelText("select 5"));
    fireEvent.click(screen.getByLabelText("select all rows"));
    expect(screen.getByText("picked 2")).toBeInTheDocument();
    expect(screen.getByLabelText("select all rows")).toBeChecked();
    fireEvent.click(screen.getByLabelText("select all rows"));
    expect(screen.getByText("picked 0")).toBeInTheDocument();
  });

  it("says when the clipboard is unavailable", async () => {
    writeText.mockRejectedValue(new Error("denied"));
    render(table());
    fireEvent.click(screen.getByRole("button", { name: "Copy for Claude" }));
    expect(
      await screen.findByText("Copy for Claude: copy failed"),
    ).toBeInTheDocument();
  });

  it("names the scope, window and units in the copied header", async () => {
    render(scoped(vi.fn(), { "t.demo/rows.q": "al" }));
    fireEvent.click(screen.getByRole("button", { name: "Copy for Claude" }));
    await screen.findByText("Copy for Claude: copied");
    expect(writeText.mock.calls[0]?.[0]).toMatch(
      /^View: Demo \/ Things · window 2025-10-09 → 2025-10-10 · filters: cwd=\/r · table: search "al" · 2 of 5 matching rows · units: n=USD/,
    );
  });

  it("works without backend meta, and says when nothing matches", () => {
    const { rerender } = render(table(ROWS, null));
    expect(
      screen.getByText("2 shown of 2 matching (2 total)"),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Show all" })).toBeNull();
    rerender(table([], null));
    expect(screen.getByText("No rows match.")).toBeInTheDocument();
    expect(screen.getByLabelText("select all rows")).not.toBeChecked();
  });

  it("renders raw objects, element titles and enum filters without values", () => {
    const meta = {
      ...META,
      columns: { ...META.columns, kind: { kind: "enum" as const } },
    };
    render(
      <DataTable<Row>
        columns={[
          { key: "obj", label: "obj" },
          { key: "kind", label: "kind" },
        ]}
        id="raw"
        meta={meta}
        rowKey={(row) => String(row.n)}
        rows={ROWS}
        title={<em>Raw</em>}
      />,
    );
    expect(screen.getByText('{"a":1}')).toBeInTheDocument();
    expect(
      within(screen.getByLabelText("kind is one of")).queryAllByRole("option"),
    ).toHaveLength(0);
    cleanup();
    const long = "y".repeat(130);
    render(
      <DataTable<{ t: string }>
        columns={[{ key: "t", label: "t" }]}
        id="long"
        rowKey={(row) => row.t}
        rows={[{ t: long }]}
        title="Long"
      />,
    );
    expect(screen.getByTitle(long)).toHaveTextContent(`${"y".repeat(120)}…`);
  });
});
