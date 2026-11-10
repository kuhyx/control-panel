import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";

import { SERVER, STATUS } from "../test/fixture.ts";
import { FleetTable } from "./fleet-table.tsx";

beforeEach(() => {
  globalThis.history.replaceState(null, "", "#");
});

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

describe("FleetTable sorting", () => {
  const titles = (): string[] => {
    const cells = within(screen.getByRole("table")).getAllByRole("rowheader");
    return cells.map((cell) => cell.querySelector("a")?.textContent ?? "");
  };

  it("sorts by subsystem title regardless of case", async () => {
    const user = userEvent.setup();
    render(<FleetTable subsystems={[SERVER, ...STATUS.subsystems]} />);
    await user.click(screen.getByRole("button", { name: /Subsystem/ }));
    expect(titles()).toEqual(["Hosts / DNS blocking", "Phone focus mode", "Signal bot"]);
    await user.click(screen.getByRole("button", { name: /Subsystem/ }));
    expect(titles()).toEqual(["Signal bot", "Phone focus mode", "Hosts / DNS blocking"]);
  });

  it("sorts by unit count numerically, not as text", async () => {
    const user = userEvent.setup();
    const [phone, hosts] = STATUS.subsystems;
    // 10 units vs 9: as text "10" < "9", as numbers 9 < 10.
    const unit = SERVER.units[0]!;
    const many = { ...hosts!, title: "Many", units: Array.from({ length: 10 }, () => unit) };
    const few = { ...phone!, title: "Few", units: Array.from({ length: 9 }, () => unit) };
    render(<FleetTable subsystems={[many, few]} />);
    await user.click(screen.getByRole("button", { name: /Units/ }));
    expect(titles()).toEqual(["Few", "Many"]);
    await user.click(screen.getByRole("button", { name: /Units/ }));
    expect(titles()).toEqual(["Many", "Few"]);
  });
});

it("says so when a search matches no subsystem", async () => {
  const user = userEvent.setup();
  render(<FleetTable subsystems={STATUS.subsystems} />);
  await user.type(screen.getByLabelText("Search Subsystem"), "zzz-nothing");
  expect(
    screen.getByRole("cell", { name: "No rows match the current filters." }),
  ).toBeInTheDocument();
  expect(screen.queryByRole("link", { name: "Hosts / DNS blocking" })).not.toBeInTheDocument();
});

it("shows each category as a spoken glyph and drops the Why sentence", () => {
  render(<FleetTable subsystems={[SERVER, ...STATUS.subsystems]} />);
  expect(screen.getAllByRole("img", { name: "enforcement" })[0]).toHaveTextContent("🔒");
  expect(screen.getByRole("img", { name: "server" })).toHaveTextContent("🖥️");
  expect(screen.queryByRole("button", { name: "Why" })).not.toBeInTheDocument();
  expect(screen.queryByText("all 3 declared unit(s) armed")).not.toBeInTheDocument();
});

it("filters by state with glyph options", async () => {
  const user = userEvent.setup();
  render(<FleetTable subsystems={STATUS.subsystems} />);
  await user.click(screen.getByLabelText("Filter State"));
  const group = screen.getByRole("group", { name: "State values" });
  expect(within(group).getByRole("img", { name: "ARMED" })).toHaveTextContent("✓");
  expect(within(group).getByRole("img", { name: "NOT_INSTALLED" })).toHaveTextContent("∅");
});
