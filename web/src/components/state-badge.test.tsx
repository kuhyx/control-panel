import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { StateBadge } from "./state-badge.tsx";

describe("StateBadge", () => {
  it("speaks the state, paints its glyph and colours it with a semantic token", () => {
    render(<StateBadge state="NOT_INSTALLED" />);
    const badge = screen.getByRole("img", { name: "NOT_INSTALLED" });
    expect(badge).toHaveTextContent(/^∅$/u);
    expect(badge).not.toHaveAttribute("title");
    expect(badge.style.backgroundColor).toBe("var(--danger)");
  });
});
