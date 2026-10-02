import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { ProbeRecord } from "../lib/types.ts";

import { ProbeDot, probeLabel, probeTone } from "./probe-dot.tsx";

function probe(over: Partial<ProbeRecord>): ProbeRecord {
  return {
    detail: null,
    kind: "http",
    latency_ms: null,
    status: null,
    target: "http://127.0.0.1:1/",
    up: true,
    ...over,
  };
}

describe("probeLabel", () => {
  it("reports the status and latency of a live endpoint", () => {
    expect(probeLabel(probe({ latency_ms: 30.2, status: 200 }))).toBe(
      "up 200 · 30.2 ms",
    );
  });

  it("says 'open' for a TCP probe that has no HTTP status", () => {
    expect(probeLabel(probe({ kind: "tcp" }))).toBe("up open");
  });

  it("names why an endpoint is down", () => {
    expect(probeLabel(probe({ detail: "refused", up: false }))).toBe(
      "down: refused",
    );
    expect(probeLabel(probe({ up: false }))).toBe("down: no answer");
  });

  it("explains an endpoint that was deliberately not probed", () => {
    expect(probeLabel(probe({ detail: "not probed: public", up: null }))).toBe(
      "not probed: public",
    );
    expect(probeLabel(probe({ up: null }))).toBe("not probed");
  });
});

describe("probeTone", () => {
  it("uses the semantic tones, muted for a skipped probe", () => {
    expect(probeTone(probe({}))).toBe("var(--success)");
    expect(probeTone(probe({ up: false }))).toBe("var(--danger)");
    expect(probeTone(probe({ up: null }))).toBe("var(--text-muted)");
  });
});

it("renders an accessible dot carrying the label", () => {
  render(<ProbeDot probe={probe({ status: 200 })} />);
  const dot = screen.getByRole("img", { name: "up 200" });
  expect(dot).toHaveAttribute("title", "up 200");
  expect(dot.style.backgroundColor).toBe("var(--success)");
});
