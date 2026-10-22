import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { stubSessionsFetch } from "../../test/sessions-fixture.ts";
import { stubTokensFetch } from "../../test/tokens-fetch.ts";
import { SessionsPage } from "../sessions/sessions-page.tsx";
import { PageTabs } from "./page-tabs.tsx";
import { TokensPage } from "./tokens-page.tsx";

afterEach(() => {
  vi.unstubAllGlobals();
});

function current(): string[] {
  return screen
    .getAllByRole("link")
    .filter((link) => link.getAttribute("aria-current") === "page")
    .map((link) => link.textContent);
}

describe("PageTabs", () => {
  it("links both tabs and marks only the active one", () => {
    render(<PageTabs active="spend" />);
    const nav = screen.getByRole("navigation", { name: "Token views" });
    expect(nav).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Spend" })).toHaveAttribute(
      "href",
      "#/tokens",
    );
    expect(screen.getByRole("link", { name: "Sessions" })).toHaveAttribute(
      "href",
      "#/tokens/sessions",
    );
    expect(current()).toEqual(["Spend"]);
  });

  it("sits on the Spend page with Spend current", () => {
    stubTokensFetch();
    render(<TokensPage route={{ id: "", name: "tokens" }} />);
    expect(current()).toEqual(["Spend"]);
  });

  it("sits on the Sessions page with Sessions current", () => {
    stubSessionsFetch();
    render(<SessionsPage />);
    expect(current()).toEqual(["Sessions"]);
  });
});
