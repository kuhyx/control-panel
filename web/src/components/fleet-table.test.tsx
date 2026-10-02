import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { SERVER, STATUS } from "../test/fixture.ts";
import { FleetTable } from "./fleet-table.tsx";

describe("FleetTable", () => {
  it("puts what is not firing above what is", () => {
    render(<FleetTable subsystems={STATUS.subsystems} />);
    const rows = within(screen.getByRole("table")).getAllByRole("row").slice(1);
    expect(rows[0]).toHaveTextContent("Phone focus mode");
    expect(rows[1]).toHaveTextContent("Hosts / DNS blocking");
  });

  it("links each subsystem to its detail route", () => {
    render(<FleetTable subsystems={STATUS.subsystems} />);
    expect(screen.getByRole("link", { name: "Hosts / DNS blocking" })).toHaveAttribute(
      "href",
      "#/s/hosts",
    );
  });

  it("marks only the rows that need attention", () => {
    render(<FleetTable subsystems={STATUS.subsystems} />);
    const rows = within(screen.getByRole("table")).getAllByRole("row").slice(1);
    expect(rows[0]).toHaveClass("row-attention");
    expect(rows[1]).not.toHaveClass("row-attention");
  });
});

it("links straight to each subsystem's dashboards", () => {
  render(<FleetTable subsystems={[SERVER, ...STATUS.subsystems]} />);
  expect(screen.getByRole("link", { name: "Manage UI" })).toHaveAttribute(
    "href",
    "http://127.0.0.1:8140/",
  );
});
