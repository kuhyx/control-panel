import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { EMPTY_QUERY } from "../../lib/tokens-api.ts";
import { stubHangingFetch, stubTokensFetch } from "../../test/tokens-fetch.ts";
import { INDEX } from "../../test/tokens-fixture.ts";
import { FilterBar } from "./filter-bar.tsx";
import { TokensPage } from "./tokens-page.tsx";

const PAGE = { id: "", name: "tokens" };

beforeEach(() => {
  globalThis.history.replaceState(null, "", "#/tokens");
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("TokensPage", () => {
  it("reads, then shows the coverage line and every panel", async () => {
    stubTokensFetch();
    render(<TokensPage route={PAGE} />);
    expect(screen.getByText("Reading…")).toBeInTheDocument();
    await waitFor(() => {
      expect(
        screen.getByRole("heading", { name: "Spend" }),
      ).toBeInTheDocument();
    });
    expect(screen.getByText("Sonnet arm within tolerance")).toBeInTheDocument();
    expect(screen.getByText(/Full per-session detail from/)).toHaveTextContent(
      /from 2026-09-01 to —; .* from 2026-01-01; prompt counts from —\./,
    );
    for (const id of [
      "Efficiency (weekly)",
      "Levers",
      "Context files",
      "Sessions by cost",
    ]) {
      expect(
        await screen.findByRole("heading", { name: id }),
      ).toBeInTheDocument();
    }
  });

  it("dashes whichever coverage bounds are unknown", async () => {
    const coverage = {
      ...INDEX.coverage,
      aggregate_from: null,
      any_from: "2025-01-01",
      detail_from: null,
      detail_to: "2026-10-10",
    };
    stubTokensFetch([], { ...INDEX, coverage });
    render(<TokensPage route={PAGE} />);
    expect(
      await screen.findByText(/Full per-session detail from/),
    ).toHaveTextContent(
      /from — to 2026-10-10; .* from —; prompt counts from 2025-01-01\./,
    );
  });

  it("starts from the hash query and writes filter changes back to it", async () => {
    globalThis.history.replaceState(null, "", "#/tokens?model=claude-opus");
    const spy = stubTokensFetch();
    render(<TokensPage route={PAGE} />);
    await waitFor(() => {
      expect(
        screen.getByRole("heading", { name: "Spend" }),
      ).toBeInTheDocument();
    });
    expect(spy).toHaveBeenCalledWith(
      "/api/tokens/panel/overview?model=claude-opus",
      {
        signal: expect.any(AbortSignal) as AbortSignal,
      },
    );
    fireEvent.change(screen.getByLabelText("scope"), {
      target: { value: "sub" },
    });
    expect(globalThis.location.hash).toBe(
      "#/tokens?model=claude-opus&scope=sub",
    );
    fireEvent.change(screen.getByLabelText("scope"), {
      target: { value: "all" },
    });
    fireEvent.change(screen.getByLabelText("model"), {
      target: { value: "" },
    });
    expect(globalThis.location.hash).toBe("#/tokens");
    await waitFor(() => {
      expect(spy).toHaveBeenCalledWith(
        "/api/tokens/panel/overview?model=claude-opus&scope=sub",
        expect.anything(),
      );
    });
  });

  it("shows a panel failure instead of the panels", async () => {
    stubTokensFetch(["/panel/levers"]);
    render(<TokensPage route={PAGE} />);
    expect(await screen.findByRole("alert")).toHaveTextContent(
      /^Levers: .*responded 500/,
    );
    expect(screen.queryByText("Reading…")).toBeNull();
    expect(
      screen.getByRole("form", { name: "Token filters" }),
    ).toBeInTheDocument();
  });

  it("shows an index failure even when the panels load", async () => {
    const spy = vi.fn((path: string) => {
      const isIndex = path === "/api/tokens";
      return Promise.resolve({
        json: () => Promise.resolve({}),
        ok: !isIndex,
        status: isIndex ? 500 : 200,
      });
    });
    vi.stubGlobal("fetch", spy);
    render(<TokensPage route={PAGE} />);
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "/api/tokens responded 500",
    );
    expect(screen.queryByRole("status")).toBeNull();
    expect(screen.queryByRole("heading", { name: "Spend" })).toBeNull();
  });

  it("drops a request cut short by unmounting", () => {
    stubHangingFetch();
    const { unmount } = render(<TokensPage route={PAGE} />);
    unmount();
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("routes to one session under the banner, its table state in the hash", async () => {
    const spy = stubTokensFetch();
    render(<TokensPage route={{ id: "sess-1", name: "tokens-session" }} />);
    expect(await screen.findByText("← all sessions")).toBeInTheDocument();
    fireEvent.click(screen.getAllByRole("button", { name: "USD" })[0]!);
    expect(globalThis.location.hash).toBe(
      "#/tokens/s/sess-1?t.session%2Fprompts.sort=-usd",
    );
    await waitFor(() => {
      expect(spy).toHaveBeenCalledWith(
        "/api/tokens/session/sess-1?t.prompts.sort=-usd",
        expect.anything(),
      );
    });
    expect(
      await screen.findByText("Sonnet arm within tolerance"),
    ).toBeInTheDocument();
  });

  it("routes to one context file, using the context panel's row once loaded", async () => {
    stubTokensFetch();
    render(
      <TokensPage
        route={{ id: "/home/kuhy/.claude/CLAUDE.md", name: "tokens-file" }}
      />,
    );
    expect(await screen.findByText(/1,000 tokens loaded/)).toBeInTheDocument();
  });
});

describe("FilterBar", () => {
  it("reports each edited field merged into the current query", () => {
    const onChange = vi.fn();
    render(<FilterBar index={INDEX} onChange={onChange} query={EMPTY_QUERY} />);
    expect(screen.getByRole("option", { name: "~/src/a" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "/srv/b" })).toBeInTheDocument();
    const edits: [string, string, string][] = [
      ["from", "2026-09-01", "from"],
      ["to", "2026-09-30", "to"],
      ["snapshot window", "2026-10-01-window", "window"],
      ["repo / cwd", "/srv/b", "cwd"],
      ["model", "claude-opus", "model"],
      ["scope", "main", "scope"],
    ];
    for (const [label, value, key] of edits) {
      fireEvent.change(screen.getByLabelText(label), { target: { value } });
      expect(onChange).toHaveBeenLastCalledWith({
        ...EMPTY_QUERY,
        [key]: value,
      });
    }
    fireEvent.submit(screen.getByRole("form", { name: "Token filters" }));
  });

  it("shows one panel alone on its own route, keeping its hash", async () => {
    stubTokensFetch();
    render(<TokensPage route={{ id: "levers", name: "tokens-panel" }} />);
    expect(
      await screen.findByRole("heading", { name: "Levers" }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Spend" })).toBeNull();
    fireEvent.change(screen.getByLabelText("scope"), {
      target: { value: "sub" },
    });
    expect(globalThis.location.hash).toBe("#/tokens/p/levers?scope=sub");
  });
});
