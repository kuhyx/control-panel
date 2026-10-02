import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { SERVER } from "../test/fixture.ts";
import { DashboardLinks } from "./dashboard-links.tsx";
import { ProbeList } from "./probe-list.tsx";

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

  it("spells out the URL and probe result in the detailed form", () => {
    render(<DashboardLinks dashboards={SERVER.dashboards} detailed />);
    expect(
      screen.getByText("http://127.0.0.1:8140/ · up 200 · 30.2 ms"),
    ).toBeInTheDocument();
  });
});

it("lists probes with their kind and result", () => {
  render(<ProbeList probes={SERVER.probes} />);
  expect(screen.getByText("127.0.0.1:8137")).toBeInTheDocument();
  expect(
    screen.getByText("tcp · down: [Errno 111] Connection refused"),
  ).toBeInTheDocument();
});
