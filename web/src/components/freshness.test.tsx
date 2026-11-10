import { act, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { Freshness } from "./freshness.tsx";

const AT = "2026-08-28T16:40:00+00:00";

describe("Freshness", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("counts up once a second without a new snapshot", () => {
    vi.useFakeTimers();
    vi.setSystemTime(Date.parse(AT) + 3000);
    render(<Freshness at={AT} />);
    expect(screen.getByRole("img", { name: "updated" })).toBeInTheDocument();
    expect(screen.getByText("3 s")).toBeInTheDocument();
    act(() => {
      vi.advanceTimersByTime(2000);
    });
    expect(screen.getByText("5 s")).toBeInTheDocument();
  });
});
