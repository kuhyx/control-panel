import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { StateBadge } from "./state-badge.tsx";

describe("StateBadge", () => {
  it("names the state and colours it with a semantic token", () => {
    render(<StateBadge state="NOT_INSTALLED" />);
    const badge = screen.getByTitle("NOT_INSTALLED");
    expect(badge).toHaveTextContent("NOT_INSTALLED");
    expect(badge.style.backgroundColor).toBe("var(--danger)");
  });
});
