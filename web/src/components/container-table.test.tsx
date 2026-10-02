import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as api from "../lib/api.ts";
import { SERVER } from "../test/fixture.ts";
import { ContainerTable } from "./container-table.tsx";

describe("ContainerTable", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("offers a restart only for containers the manifest marks restartable", () => {
    render(<ContainerTable containers={SERVER.containers} />);
    expect(
      screen.getByRole("button", { name: "Restart signal-api" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Restart ghost" }),
    ).not.toBeInTheDocument();
  });

  it("shows docker's own status beside the state", () => {
    render(<ContainerTable containers={SERVER.containers} />);
    expect(screen.getByText("Up 4 days (healthy)")).toBeInTheDocument();
    // A container Docker has never heard of has no state; say so with a dash.
    const ghost = screen.getByRole("row", { name: /ghost/ });
    expect(within(ghost).getByText("—")).toBeInTheDocument();
  });

  it("opens and closes the container's log in a row of its own", async () => {
    const spy = vi.spyOn(api, "fetchJournal").mockResolvedValue({
      error: "",
      lines: ["2026-10-02T14:57:15Z ready"],
      name: "signal-api",
      ok: true,
      source: "docker",
    });
    const user = userEvent.setup();
    render(<ContainerTable containers={SERVER.containers} />);
    await user.click(
      screen.getByRole("button", { name: "Show logs for signal-api" }),
    );
    expect(spy).toHaveBeenCalledWith(
      "docker",
      "signal-api",
      100,
      expect.any(AbortSignal),
    );
    expect(await screen.findByText(/ready/)).toBeInTheDocument();
    await user.click(
      screen.getByRole("button", { name: "Hide logs for signal-api" }),
    );
    expect(screen.queryByText(/ready/)).not.toBeInTheDocument();
  });
});
