import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { EMPTY_QUERY } from "../../lib/tokens-api.ts";
import { INDEX } from "../../test/tokens-fixture.ts";
import { LazyPanel } from "./lazy-panel.tsx";
import { useScope } from "./table-scope.tsx";

function Probe({ data }: Readonly<{ data: unknown }>): React.JSX.Element {
  const scope = useScope();
  return (
    <p>
      got {JSON.stringify(data)} in {scope?.panel}{" "}
      {String(scope?.window?.since)}
    </p>
  );
}

const VIEW = {
  name: "demo",
  order: 1,
  render: (data: unknown) => <Probe data={data} />,
  title: "Demo",
};

function stub(body: unknown, isOk = true): void {
  vi.stubGlobal(
    "fetch",
    vi.fn(() => {
      return Promise.resolve({
        json: () => Promise.resolve(body),
        ok: isOk,
        status: isOk ? 200 : 500,
      });
    },
    ),
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("LazyPanel", () => {
  it("reads, then renders the view inside its own table scope", async () => {
    stub({ filters: { since: 7, until: 9 } });
    const query = {
      ...EMPTY_QUERY,
      cwd: "/x",
      tables: { "t.demo/a.q": "z", "t.other/b.q": "y" },
    };
    render(
      <LazyPanel index={INDEX} onQuery={vi.fn()} query={query} view={VIEW} />,
    );
    expect(screen.getByText("Reading Demo…")).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText(/in demo 7$/)).toBeInTheDocument();
    });
    expect(fetch).toHaveBeenCalledWith(
      "/api/tokens/panel/demo?cwd=%2Fx&t.a.q=z",
      expect.anything(),
    );
  });

  it("has no window when the panel answers without filters", async () => {
    stub({});
    render(
      <LazyPanel
        index={INDEX}
        onQuery={vi.fn()}
        query={EMPTY_QUERY}
        view={VIEW}
      />,
    );
    expect(await screen.findByText(/in demo undefined$/)).toBeInTheDocument();
  });

  it("shows a per-panel error instead of blanking the page", async () => {
    stub(null, false);
    render(
      <LazyPanel
        index={INDEX}
        onQuery={vi.fn()}
        query={EMPTY_QUERY}
        view={VIEW}
      />,
    );
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(
        /^Demo: .*responded 500/,
      );
    });
  });
});
