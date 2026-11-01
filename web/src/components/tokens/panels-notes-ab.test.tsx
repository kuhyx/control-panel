import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AB, EFFICIENCY } from "../../test/tokens-fixture.ts";
import { AbPanel } from "./ab-panel.tsx";
import { EfficiencyPanel } from "./efficiency-panel.tsx";

function row(name: string): HTMLElement {
  const found = screen.getByRole("cell", { name }).closest("tr");
  if (found === null) throw new Error(`no row for ${name}`);
  return found;
}

describe("EfficiencyPanel notes", () => {
  it("charts USD per note and lists notes by cost", () => {
    render(
      <EfficiencyPanel
        data={{
          ...EFFICIENCY,
          captions: { ...EFFICIENCY.captions, notes: "Notes caption." },
          notes: [
            {
              done: "2026-09-02",
              done_at: 1,
              id: "n1",
              priority: "high",
              sessions: 2,
              status: "done",
              title: "fix the locker",
              tokens: 1000,
              usd: 12.5,
            },
          ],
          notes_weekly: [{ abandoned: 0, done: 1, usd: 12.5, usd_per_note: 12.5, week: "2026-08-31" }],
        }}
      />,
    );
    expect(screen.getByText("Notes caption.")).toBeInTheDocument();
    expect(row("fix the locker")).toHaveTextContent("12.5");
    expect(screen.getByRole("img", { name: "USD per note" })).toBeInTheDocument();
  });
});

describe("AbPanel build experiment", () => {
  it("shows the build experiment under its own heading", () => {
    render(
      <AbPanel
        data={{
          ...AB,
          build: {
            arms: {},
            banner: { level: "grey", text: "A/B build agents: collecting (n=0)" },
            metrics: [{ difference: "—", measure: "build n", opus: "0", sonnet: "1" }],
            unjoined: 5,
          },
        }}
      />,
    );
    expect(row("build n")).toHaveTextContent("1");
    expect(screen.getByRole("heading", { name: /build subagents/ })).toBeInTheDocument();
    expect(screen.getByText("A/B build agents: collecting (n=0)")).toBeInTheDocument();
    expect(screen.getByText(/5 build assignments not/)).toBeInTheDocument();
  });

  it("defaults a sparse build payload", () => {
    render(<AbPanel data={{ ...AB, build: { arms: {}, banner: AB.banner } }} />);
    expect(screen.getByText(/0 build assignments not/)).toBeInTheDocument();
  });
});
