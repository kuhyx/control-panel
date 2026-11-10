import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { STATUS } from "../test/fixture.ts";
import { AnomalyBanner } from "./anomaly-banner.tsx";

describe("AnomalyBanner", () => {
  it("speaks each real finding and counts them in the heading", () => {
    render(<AnomalyBanner anomalies={STATUS.anomalies} />);
    expect(
      screen.getByRole("listitem", {
        name: /^phone-auto-sync\.timer is NOT_INSTALLED: /u,
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("listitem", { name: /^kuhytrack-budget\.timer is UNARMED: /u }),
    ).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Findings" })).toHaveTextContent("2");
  });

  it("links each finding to the subsystem it is about", () => {
    render(<AnomalyBanner anomalies={STATUS.anomalies} />);
    const [first, second] = within(screen.getByRole("list")).getAllByRole("listitem");
    if (first === undefined || second === undefined) throw new Error("two findings expected");
    expect(within(first).getByRole("link")).toHaveAttribute(
      "href",
      "#/s/phone-focus-mode",
    );
    expect(within(second).getByRole("link")).toHaveAttribute(
      "href",
      "#/s/kuhytrack",
    );
  });

  it("shows a check when nothing needs attention", () => {
    render(<AnomalyBanner anomalies={[]} />);
    expect(screen.getByRole("status")).toHaveAccessibleName("Nothing needs attention");
  });
});
