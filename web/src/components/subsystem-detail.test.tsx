import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { SubsystemStatus } from "../lib/types.ts";

import { SERVER, STATUS } from "../test/fixture.ts";
import { SubsystemDetail } from "./subsystem-detail.tsx";

const [phone, hosts] = STATUS.subsystems as [SubsystemStatus, SubsystemStatus];

describe("SubsystemDetail", () => {
  it("shows the facts that explain why a subsystem exists", () => {
    render(<SubsystemDetail subsystem={phone} />);
    expect(screen.getByText("installer")).toBeInTheDocument();
    expect(
      screen.getByText("~/src/phone-focus-mode/systemd/install.sh"),
    ).toBeInTheDocument();
  });

  it("omits the facts and logs sections when there are none", () => {
    render(<SubsystemDetail subsystem={phone} />);
    expect(screen.queryByText("Logs")).not.toBeInTheDocument();
  });

  it("lists logs with their size and links to the viewer", () => {
    render(<SubsystemDetail subsystem={hosts} />);
    expect(
      screen.getByRole("link", { name: "/var/log/hosts-file-monitor.log" }),
    ).toHaveAttribute("href", "#/logs/hosts-monitor");
    expect(screen.getByText("54.6 MB")).toBeInTheDocument();
  });

  it("calls out a log with no logrotate entry", () => {
    const unrotated: SubsystemStatus = {
      ...hosts,
      logs: [{ ...hosts.logs[0]!, rotated: false }],
    };
    render(<SubsystemDetail subsystem={unrotated} />);
    expect(screen.getByText(/no logrotate entry/)).toBeInTheDocument();
  });

  it("falls back to the unit name for a journal log", () => {
    const journal: SubsystemStatus = {
      ...hosts,
      logs: [
        {
          bytes: null,
          id: "j",
          kind: "journal",
          mtime: null,
          path: null,
          rotated: null,
          scope: "user",
          unit: "hosts-file-monitor.service",
        },
      ],
    };
    render(<SubsystemDetail subsystem={journal} />);
    expect(
      screen.getByRole("link", { name: "hosts-file-monitor.service" }),
    ).toBeInTheDocument();
    expect(screen.getByText("journal")).toBeInTheDocument();
  });
});

describe("writable knobs", () => {
  it("offers the curfew form only on the shutdown subsystem", () => {
    render(<SubsystemDetail subsystem={{ ...hosts, id: "shutdown" }} />);
    expect(
      screen.getByRole("region", { name: "Tighten the curfew" }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Block a domain" })).toBeNull();
  });

  it("offers the block form only on the hosts subsystem", () => {
    render(<SubsystemDetail subsystem={hosts} />);
    expect(
      screen.getByRole("region", { name: "Block a domain" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("region", { name: "Tighten the curfew" }),
    ).toBeNull();
  });

  it("offers no knob at all on a read-only subsystem", () => {
    // Eleven of the thirteen subsystems have no writable surface, and that is
    // the design rather than an omission.
    render(<SubsystemDetail subsystem={phone} />);
    expect(screen.queryByRole("region", { name: /Tighten|Block/ })).toBeNull();
  });
});

it("shows a server's dashboards, containers and probes", () => {
  render(<SubsystemDetail subsystem={SERVER} />);
  expect(screen.getByRole("heading", { name: "Dashboards" })).toBeInTheDocument();
  expect(screen.getByText(/up 200 · 30.2 ms/)).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Containers" })).toBeInTheDocument();
  expect(screen.getByText("signal-api")).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Probes" })).toBeInTheDocument();
  expect(screen.getByText("127.0.0.1:8137")).toBeInTheDocument();
});

it("omits the running sections for a subsystem that has none", () => {
  render(<SubsystemDetail subsystem={phone} />);
  expect(screen.queryByRole("heading", { name: "Dashboards" })).not.toBeInTheDocument();
  expect(screen.queryByRole("heading", { name: "Containers" })).not.toBeInTheDocument();
  expect(screen.queryByRole("heading", { name: "Probes" })).not.toBeInTheDocument();
});
