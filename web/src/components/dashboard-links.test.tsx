import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { DashboardRecord } from "../lib/types.ts";

import { SERVER } from "../test/fixture.ts";
import { DashboardLinks } from "./dashboard-links.tsx";
import { ProbeList } from "./probe-list.tsx";

const ON_DEMAND: DashboardRecord = {
  clash: null,
  label: "mangatl",
  on_demand: true,
  probe: {
    detail: "not probed: on demand",
    kind: "http",
    latency_ms: null,
    status: null,
    target: "",
    up: null,
  },
  stopped: false,
  url: "http://127.0.0.1:8781/",
};

describe("DashboardLinks", () => {
  it("renders nothing when a subsystem has no dashboards", () => {
    const { container } = render(<DashboardLinks dashboards={[]} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("opens every dashboard in a new tab without handing it an opener", () => {
    render(<DashboardLinks dashboards={SERVER.dashboards} />);
    const link = screen.getByRole("link", { name: "Manage UI" });
    expect(link).toHaveAttribute("href", "http://127.0.0.1:8140/");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
  });

  it("keeps the compact form to links and dots", () => {
    render(<DashboardLinks dashboards={SERVER.dashboards} />);
    expect(screen.queryByText(/30.2 ms/)).not.toBeInTheDocument();
    expect(screen.getByRole("img", { name: "not probed: public" })).toBeInTheDocument();
  });

  it("renders a stopped on-demand dashboard as text, not a dead link", () => {
    const stopped: DashboardRecord = {
      ...ON_DEMAND,
      stopped: true,
    };
    render(<DashboardLinks dashboards={[stopped]} />);
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
    expect(screen.getByText("mangatl")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "stopped" })).toHaveTextContent("⏸");
    expect(
      screen.getByRole("img", { name: "stopped (on demand)" }),
    ).toBeInTheDocument();
  });

  it("keeps a running on-demand dashboard clickable", () => {
    render(<DashboardLinks dashboards={[ON_DEMAND]} />);
    expect(screen.getByRole("link", { name: "mangatl" })).toHaveAttribute(
      "href",
      "http://127.0.0.1:8781/",
    );
  });

  it("names the foreign owner of a clashing port instead of linking to it", () => {
    const clash = "port 8780 held by anki-syncserver.service (pid 1735)";
    render(
      <DashboardLinks
        dashboards={[{ ...ON_DEMAND, clash, stopped: true }]}
        detailed
      />,
    );
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
    expect(screen.getByRole("img", { name: "stopped · port taken" })).toHaveTextContent(
      "⏸ ⚠",
    );
    // The owner is spoken on the dot, not painted.
    expect(screen.getByRole("img", { name: clash })).toBeInTheDocument();
    expect(screen.queryByText(new RegExp(clash, "u"))).not.toBeInTheDocument();
    expect(screen.getByText("http://127.0.0.1:8781/")).toBeInTheDocument();
  });

  it("marks a clash alone with the warning glyph", () => {
    const clash = "port 8780 held by anki-syncserver.service (pid 1735)";
    render(<DashboardLinks dashboards={[{ ...ON_DEMAND, clash }]} />);
    expect(screen.getByRole("img", { name: "port taken" })).toHaveTextContent("⚠");
  });

  it("adds the URL and the probe's numbers in the detailed form", () => {
    render(<DashboardLinks dashboards={SERVER.dashboards} detailed />);
    expect(
      screen.getByText("http://127.0.0.1:8140/ · 200 · 30.2 ms"),
    ).toBeInTheDocument();
    // A probe that never ran has no numbers: the URL stands alone.
    expect(screen.getByText("https://popes.kuhy.duckdns.org/")).toBeInTheDocument();
  });
});

it("lists probes with a kind glyph, the sentence spoken on the dot", () => {
  render(<ProbeList probes={SERVER.probes} />);
  expect(screen.getByText("127.0.0.1:8137")).toBeInTheDocument();
  expect(screen.getByRole("img", { name: "tcp" })).toHaveTextContent("🔌");
  expect(
    screen.getByRole("img", { name: "down: [Errno 111] Connection refused" }),
  ).toBeInTheDocument();
});

it("falls back to a bullet for a probe kind it does not know", () => {
  render(
    <ProbeList
      probes={[
        { detail: null, kind: "icmp", latency_ms: 4, status: null, target: "localhost", up: true },
      ]}
    />,
  );
  expect(screen.getByRole("img", { name: "icmp" })).toHaveTextContent("•");
  expect(screen.getByText(/4 ms/u)).toBeInTheDocument();
});
