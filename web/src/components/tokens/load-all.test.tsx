import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { EMPTY_QUERY } from "../../lib/tokens-api.ts";
import { DETAIL } from "../../test/tokens-fetch.ts";
import { INDEX } from "../../test/tokens-fixture.ts";
import { DataTable } from "./data-table.tsx";
import { LazyPanel, loadAll } from "./lazy-panel.tsx";
import { SessionDetail } from "./session-detail.tsx";
import { useScope } from "./table-scope.tsx";

const CUT = { columns: {}, matched: 2, shown: 1, total: 2 };

function reply(...bodies: unknown[]): ReturnType<typeof vi.fn> {
  const spy = vi.fn();
  for (const body of bodies) {
    spy.mockResolvedValueOnce({
      json: () => Promise.resolve(body),
      ok: true,
      status: 200,
    });
  }
  vi.stubGlobal("fetch", spy);
  return spy;
}

function stubClipboard(): ReturnType<typeof vi.fn> {
  const writeText = vi.fn<(text: string) => Promise<void>>(() =>
    Promise.resolve(),
  );
  vi.stubGlobal("navigator", { clipboard: { writeText } });
  return writeText;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("loadAll", () => {
  it("refetches one panel table with its limit lifted", async () => {
    const spy = reply({ rows: [{ n: 1 }, { n: 2 }] }, {});
    const query = { ...EMPTY_QUERY, tables: { "t.demo/rows.limit": "5" } };
    expect(await loadAll("demo", query, "rows")).toEqual([{ n: 1 }, { n: 2 }]);
    expect(spy).toHaveBeenCalledWith(
      "/api/tokens/panel/demo?t.rows.limit=0",
      expect.anything(),
    );
    expect(await loadAll("demo", query, "rows")).toEqual([]);
  });

  it("is what a lazy panel's tables get in their scope", async () => {
    function Probe(): React.JSX.Element {
      const scope = useScope();
      return (
        <button
          onClick={() => {
            void scope?.loadAll?.("rows");
          }}
          type="button"
        >
          load
        </button>
      );
    }
    const spy = reply({ filters: { since: 0, until: 1 } }, { rows: [] });
    const view = {
      name: "demo",
      order: 1,
      render: () => <Probe />,
      title: "Demo",
    };
    render(
      <LazyPanel
        index={INDEX}
        onQuery={vi.fn()}
        query={EMPTY_QUERY}
        view={view}
      />,
    );
    fireEvent.click(await screen.findByRole("button", { name: "load" }));
    await waitFor(() => {
      expect(spy).toHaveBeenLastCalledWith(
        "/api/tokens/panel/demo?t.rows.limit=0",
        expect.anything(),
      );
    });
  });

  it("refetches a session table, and nested tables copy their own rows", async () => {
    const writeText = stubClipboard();
    const first = { ...DETAIL, _tables: { prompts: CUT } };
    const spy = reply(
      first,
      { ...DETAIL, prompts: [{ ...DETAIL.prompts[0], text: "ALL" }] },
      {},
    );
    render(<SessionDetail id="sess-1" onQuery={vi.fn()} />);
    const [copy] = await screen.findAllByRole("button", {
      name: "Copy as JSON",
    });
    fireEvent.click(copy!);
    await waitFor(() => {
      expect(String(writeText.mock.lastCall?.[0])).toContain('"text": "ALL"');
    });
    expect(spy).toHaveBeenLastCalledWith(
      "/api/tokens/session/sess-1?t.prompts.limit=0",
      expect.anything(),
    );
    fireEvent.click(copy!);
    await waitFor(() => {
      expect(writeText).toHaveBeenCalledTimes(2);
    });
    expect(String(writeText.mock.lastCall?.[0])).toContain('"rows": []');
  });

  it("never refetches a nested table", async () => {
    const writeText = stubClipboard();
    const fetchAll = vi.fn(() => Promise.resolve([]));
    const scope = {
      loadAll: fetchAll,
      onQuery: vi.fn(),
      panel: "p",
      query: EMPTY_QUERY,
      title: "P",
      window: null,
    };
    const { TableScope } = await import("./table-scope.tsx");
    render(
      <TableScope scope={scope}>
        <DataTable<{ n: number }>
          columns={[{ key: "n", label: "n" }]}
          id="prompts.tools"
          meta={CUT}
          rowKey={(row) => String(row.n)}
          rows={[{ n: 1 }]}
          title="Tools"
        />
      </TableScope>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Copy as JSON" }));
    await screen.findByText("Copy as JSON: copied");
    expect(fetchAll).not.toHaveBeenCalled();
    expect(String(writeText.mock.lastCall?.[0])).toContain('"n": 1');
  });
});
