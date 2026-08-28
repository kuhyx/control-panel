import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { STATUS } from "../test/fixture.ts";
import { UnitTable } from "./unit-table.tsx";

const [phone, hosts] = STATUS.subsystems;

describe("UnitTable", () => {
  it("says a unit is not installed rather than showing a blank state", () => {
    render(<UnitTable units={phone!.units} />);
    expect(screen.getByText("not installed")).toBeInTheDocument();
  });

  it("renders the next run as a real date, not an epoch in 1970", () => {
    render(<UnitTable units={hosts!.units} />);
    const row = within(screen.getByRole("table")).getAllByRole("row")[1];
    expect(row).toHaveTextContent("2026");
    expect(row).not.toHaveTextContent("1970");
  });

  it("flags a unit whose preset disagrees with its state", () => {
    render(<UnitTable units={hosts!.units} />);
    expect(screen.getByText("preset disabled")).toBeInTheDocument();
  });

  it("explains an empty unit list instead of showing an empty table", () => {
    render(<UnitTable units={[]} />);
    expect(screen.getByText(/another mechanism/)).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });
});

it("renders a dash when an installed unit reports no unit-file state", () => {
  render(
    <UnitTable
      units={[{ ...hosts!.units[0]!, preset: null, unit_file_state: null }]}
    />,
  );
  expect(screen.getByText("—")).toBeInTheDocument();
});
