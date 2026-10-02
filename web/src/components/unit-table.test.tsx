import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import * as api from "../lib/api.ts";
import { SERVER, STATUS } from "../test/fixture.ts";
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
      units={[
        {
          ...hosts!.units[0]!,
          state: { ...hosts!.units[0]!.state, preset: null, unit_file_state: null },
        },
      ]}
    />,
  );
  expect(screen.getByText("—")).toBeInTheDocument();
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
