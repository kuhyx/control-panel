import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { SubsystemStatus } from "../lib/types.ts";

import { SERVER, STATUS } from "../test/fixture.ts";
import { SubsystemDetail } from "./subsystem-detail.tsx";

const [phone, hosts] = STATUS.subsystems as [SubsystemStatus, SubsystemStatus];

describe("SubsystemDetail", () => {
  it("shows the facts that explain why a subsystem exists", () => {
    render(<SubsystemDetail subsystem={phone} />);
    // The fact's key is spoken; its value (a path) is painted.
    expect(screen.getByLabelText("installer")).toHaveTextContent("▸");
    expect(
      screen.getByText("~/src/phone-focus-mode/systemd/install.sh"),
    ).toBeInTheDocument();
  });

  it("does not paint the server's reason sentence", () => {
    render(<SubsystemDetail subsystem={phone} />);
    expect(screen.queryByText(phone.reason)).toBeNull();
    expect(screen.queryByText(/NOT_INSTALLED:/)).toBeNull();
    expect(screen.queryByRole("img", { name: "disarmed on purpose" })).toBeNull();
  });

  it("shows a deliberate disarm's own note, without the server's prefix", () => {
    const disarmed: SubsystemStatus = {
      ...phone,
      reason: "disarmed on purpose: until the app is done (kuhy)",
      state: "DISARMED",
    };
    render(<SubsystemDetail subsystem={disarmed} />);
    expect(screen.getByRole("img", { name: "disarmed on purpose" })).toHaveTextContent("⏸");
    expect(screen.getByText(/until the app is done \(kuhy\)/)).toBeInTheDocument();
    expect(screen.queryByText(/disarmed on purpose:/)).toBeNull();
  });

  it("omits the facts and logs sections when there are none", () => {
    render(<SubsystemDetail subsystem={phone} />);
    expect(screen.queryByRole("heading", { name: "Logs" })).not.toBeInTheDocument();
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
    expect(screen.getByRole("img", { name: "no logrotate entry" })).toHaveTextContent("⚠");
    expect(screen.getByText("54.6 MB")).toBeInTheDocument();
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
    expect(screen.getByRole("img", { name: "journal" })).toBeInTheDocument();
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
  expect(screen.getByText(/ · 200 · 30.2 ms$/)).toBeInTheDocument();
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
