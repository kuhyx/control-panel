import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { DETAIL, stubHangingFetch, stubTokensFetch } from "../../test/tokens-fetch.ts";
import { CONTEXT, FILE } from "../../test/tokens-fixture.ts";
import { ContextFile } from "./context-panel.tsx";
import { SessionDetail } from "./session-detail.tsx";

function answer(body: unknown): void {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({ json: () => Promise.resolve(body), ok: true, status: 200 }),
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("SessionDetail", () => {
  it("breaks a session down by prompt, subagent and tool", async () => {
    stubTokensFetch();
    render(<SessionDetail id="sess-1" />);
    expect(screen.getByText("Reading…")).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "Fix the thing" })).toBeInTheDocument();
    expect(screen.getByText(/ended DONE/)).toBeInTheDocument();
    expect(screen.getByText("do the work")).toBeInTheDocument();
    expect(screen.getByText("↳ ↳ look around")).toBeInTheDocument();
    expect(screen.getAllByRole("cell", { name: "sonnet" }).length).toBeGreaterThan(0);
    expect(screen.getByRole("cell", { name: "Bash" })).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "60.0%" })).toBeInTheDocument();
    expect(screen.getByText(/Unattributed subagents/)).toBeInTheDocument();
  });

  it("titles an untitled session by its key and omits empty sections", async () => {
    answer({
      ...DETAIL,
      prompts: [],
      session: { ...DETAIL.session, final_tag: null, title: "" },
      unattributed: [],
    });
    render(<SessionDetail id="sess-1" />);
    expect(await screen.findByRole("heading", { name: "sess-1" })).toBeInTheDocument();
    expect(screen.getByText(/ended untagged/)).toBeInTheDocument();
    expect(screen.queryByText(/Unattributed subagents/)).toBeNull();
  });

  it("reports a failed fetch", async () => {
    stubTokensFetch(["/session/"]);
    render(<SessionDetail id="gone" />);
    expect(await screen.findByRole("alert")).toHaveTextContent(/responded 500/);
  });

  it("drops a request cut short by unmounting", () => {
    stubHangingFetch();
    const { unmount } = render(<SessionDetail id="x" />);
    unmount();
    expect(screen.queryByRole("alert")).toBeNull();
  });
});

describe("ContextFile", () => {
  it("shows the file's cost, size history, git log and content", async () => {
    stubTokensFetch();
    render(<ContextFile data={CONTEXT} path={FILE.path} />);
    expect(screen.getByText("Reading…")).toBeInTheDocument();
    expect(await screen.findByText("# rules")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "~/.claude/CLAUDE.md" })).toBeInTheDocument();
    expect(screen.getByText(/global · 1,000 tokens loaded · \$0\.25\/day · over 40k/)).toBeInTheDocument();
    expect(screen.getByRole("img", { name: `size of ${FILE.path} over time` })).toBeInTheDocument();
    expect(screen.getByText("abc123 trim rules")).toBeInTheDocument();
  });

  it("copes with a file that is gone, untracked and has no history", async () => {
    answer({ content: null, git_log: [], kind: "repo", path: "/srv/b/CLAUDE.md" });
    render(<ContextFile data={CONTEXT} path="/srv/b/CLAUDE.md" />);
    expect(await screen.findByText("(file is gone)")).toBeInTheDocument();
    expect(screen.getByText("not tracked by git")).toBeInTheDocument();
    expect(screen.getByText(/^repo · 0 tokens loaded · \$0\.00\/day$/)).toBeInTheDocument();
    expect(screen.queryByRole("img")).toBeNull();
  });

  it("shows only the kind before the context panel has loaded", async () => {
    answer(FILE);
    render(<ContextFile data={null} path={FILE.path} />);
    expect(await screen.findByText(/^global$/)).toBeInTheDocument();
  });

  it("reports a failed fetch and drops one cut short by unmounting", async () => {
    stubTokensFetch(["context-file"]);
    render(<ContextFile data={null} path="/x" />);
    expect(await screen.findByRole("alert")).toHaveTextContent(/responded 500/);
    stubHangingFetch();
    const { unmount } = render(<ContextFile data={null} path="/y" />);
    unmount();
  });
});
