import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as api from "../lib/api.ts";
import { SERVER, STATUS } from "../test/fixture.ts";
import { UnitTable } from "./unit-table.tsx";

const [phone, hosts] = STATUS.subsystems;

beforeEach(() => {
  globalThis.history.replaceState(null, "", "#");
});

describe("UnitTable", () => {
  it("marks a unit that is not installed rather than showing a blank state", () => {
    render(<UnitTable units={phone!.units} />);
    // Also an option in the Unit file filter, so look at body rows only.
    const body = within(screen.getByRole("table")).getAllByRole("row")[1]!;
    expect(within(body).getByRole("img", { name: "not installed" })).toHaveTextContent("∅");
  });

  it("paints the unit-file state and the scope as glyphs", () => {
    render(<UnitTable units={hosts!.units} />);
    const body = within(screen.getByRole("table")).getAllByRole("row")[1]!;
    expect(within(body).getByRole("img", { name: "enabled" })).toHaveTextContent("●");
    expect(within(body).getByRole("img", { name: "system" })).toHaveTextContent("#");
    expect(body).not.toHaveTextContent("enabled");
  });

  it("falls back to a bullet for an unexpected unit-file state", () => {
    render(
      <UnitTable
        units={[
          {
            ...hosts!.units[0]!,
            state: { ...hosts!.units[0]!.state, preset: null, unit_file_state: "transient" },
          },
        ]}
      />,
    );
    const body = within(screen.getByRole("table")).getAllByRole("row")[1]!;
    expect(within(body).getByRole("img", { name: "transient" })).toHaveTextContent("•");
  });

  it("renders the next run as a real date, not an epoch in 1970", () => {
    render(<UnitTable units={hosts!.units} />);
    const row = within(screen.getByRole("table")).getAllByRole("row")[1];
    expect(row).toHaveTextContent("2026");
    expect(row).not.toHaveTextContent("1970");
  });

  it("flags a unit whose preset disagrees with its state", () => {
    render(<UnitTable units={hosts!.units} />);
    expect(screen.getByRole("img", { name: "preset disabled" })).toHaveTextContent("≠○");
  });

  it("marks when a search matches no unit", async () => {
    const user = userEvent.setup();
    render(<UnitTable units={hosts!.units} />);
    await user.type(screen.getByLabelText("Search Unit"), "no-such-unit");
    expect(
      screen.getByRole("cell", { name: "No rows match the current filters." }),
    ).toHaveTextContent("∅");
    expect(screen.getByRole("status")).toHaveAccessibleName(
      `0 of ${String(hosts!.units.length)} shown`,
    );
    expect(screen.getByRole("status")).toHaveTextContent(`0/${String(hosts!.units.length)}`);
  });

  it("marks an empty unit list instead of showing an empty table", () => {
    render(<UnitTable units={[]} />);
    expect(screen.getByRole("status", { name: "No systemd units" })).toHaveTextContent("∅");
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });
});

it("renders a dash when an installed unit reports no unit-file state", () => {
  render(
    <UnitTable
      units={[
        {
          ...hosts!.units[0]!,
          state: { ...hosts!.units[0]!.state, preset: null, unit_file_state: null },
        },
      ]}
    />,
  );
  // Also an option in the Unit file filter, so look in the body row only.
  const body = within(screen.getByRole("table")).getAllByRole("row")[1]!;
  expect(within(body).getByRole("img", { name: "—" })).toHaveTextContent("—");
});

it("offers a restart only for a restartable unit", () => {
  render(<UnitTable units={[...SERVER.units, ...hosts!.units]} />);
  expect(
    screen.getByRole("button", { name: "Restart signal-bot.service" }),
  ).toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "Restart dns-blocklist-refresh.timer" }),
  ).not.toBeInTheDocument();
});

it("has no log toggle for a unit that is not installed", () => {
  render(<UnitTable units={phone!.units} />);
  expect(screen.queryByRole("button", { name: /logs for/ })).not.toBeInTheDocument();
});

it("reads a unit's journal in its own scope", async () => {
  const spy = vi.spyOn(api, "fetchJournal").mockResolvedValue({
    error: "",
    lines: ["refreshed"],
    name: "dns-blocklist-refresh.timer",
    ok: true,
    source: "system",
  });
  const user = userEvent.setup();
  render(<UnitTable units={hosts!.units} />);
  await user.click(
    screen.getByRole("button", { name: "Show logs for dns-blocklist-refresh.timer" }),
  );
  expect(spy).toHaveBeenCalledWith(
    "system",
    "dns-blocklist-refresh.timer",
    100,
    expect.any(AbortSignal),
  );
  expect(await screen.findByText("refreshed")).toBeInTheDocument();
  await user.click(
    screen.getByRole("button", { name: "Hide logs for dns-blocklist-refresh.timer" }),
  );
  expect(screen.queryByText("refreshed")).not.toBeInTheDocument();
});

it("sorts, searches and filters units, and drops Actions from the controls", async () => {
  const user = userEvent.setup();
  render(<UnitTable units={[...SERVER.units, ...hosts!.units]} />);
  const table = screen.getByRole("table");
  const unitRows = (): string[] =>
    within(table).getAllByRole("rowheader").map((cell) => cell.textContent);
  const total = unitRows().length;
  await user.type(screen.getByLabelText("Search Unit"), "SIGNAL");
  expect(unitRows().every((name) => name.includes("signal"))).toBe(true);
  expect(screen.getByRole("status")).toHaveAccessibleName(new RegExp(`of ${String(total)} shown$`, "u"));
  await user.click(screen.getByRole("button", { name: "Clear filters" }));
  expect(unitRows()).toHaveLength(total);
  await user.click(screen.getByRole("button", { name: /^Next run/ }));
  expect(globalThis.location.hash).toBe("#?units.sort=next:asc");
  expect(screen.queryByLabelText("Search Actions")).not.toBeInTheDocument();
  expect(screen.getByRole("columnheader", { name: "Actions" })).not.toHaveAttribute(
    "aria-sort",
  );
});
