import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { STATUS } from "../test/fixture.ts";
import { AnomalyBanner } from "./anomaly-banner.tsx";

describe("AnomalyBanner", () => {
  it("names the real findings, not a generic count", () => {
    render(<AnomalyBanner anomalies={STATUS.anomalies} />);
    expect(
      screen.getByText("phone-auto-sync.timer is NOT_INSTALLED"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("kuhytrack-budget.timer is UNARMED"),
    ).toBeInTheDocument();
    expect(screen.getByText("2 finding(s)")).toBeInTheDocument();
  });

  it("shows evidence when there is any, and omits the line when there is none", () => {
    render(<AnomalyBanner anomalies={STATUS.anomalies} />);
    const items = within(screen.getByRole("list")).getAllByRole("listitem");
    expect(items[0]).toHaveTextContent("scope=user · UnitFileState=None");
    expect(items[1]).not.toHaveTextContent("·");
  });

  it("says so plainly when nothing needs attention", () => {
    render(<AnomalyBanner anomalies={[]} />);
    expect(screen.getByRole("status")).toHaveTextContent(
      /Nothing needs attention/,
    );
  });
});
