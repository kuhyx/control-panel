import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as api from "../lib/api.ts";
import { RestartButton } from "./restart-button.tsx";

describe("RestartButton", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("asks for a second click before restarting anything", async () => {
    const spy = vi.spyOn(api, "restart");
    const user = userEvent.setup();
    render(<RestartButton kind="unit" name="signal-bot.service" />);
    await user.click(
      screen.getByRole("button", { name: "Restart signal-bot.service" }),
    );
    expect(spy).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Confirm restart" })).toBeInTheDocument();
  });

  it("can be cancelled", async () => {
    const spy = vi.spyOn(api, "restart");
    const user = userEvent.setup();
    render(<RestartButton kind="unit" name="a.service" />);
    await user.click(screen.getByRole("button", { name: "Restart a.service" }));
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(spy).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Restart a.service" })).toBeInTheDocument();
  });

  it("restarts once confirmed and shows the server's answer", async () => {
    const pending = Promise.withResolvers<Awaited<ReturnType<typeof api.restart>>>();
    const spy = vi.spyOn(api, "restart").mockReturnValue(pending.promise);
    const user = userEvent.setup();
    render(<RestartButton kind="container" name="gitea" />);
    await user.click(screen.getByRole("button", { name: "Restart gitea" }));
    await user.click(screen.getByRole("button", { name: "Confirm restart" }));
    expect(spy).toHaveBeenCalledWith("container", "gitea");
    // While the request is in flight the button says so and cannot be re-sent.
    expect(screen.getByRole("button", { name: "Restart gitea" })).toBeDisabled();
    expect(screen.getByText("Restarting…")).toBeInTheDocument();
    pending.resolve({
      argv: ["docker", "restart", "gitea"],
      ok: true,
      refused: false,
      stderr: "",
      stdout: "",
      summary: "gitea restarted.",
    });
    await waitFor(() => {
      expect(screen.getByText("gitea restarted.")).toBeInTheDocument();
    });
  });

  it("shows a transport failure instead of swallowing it", async () => {
    vi.spyOn(api, "restart").mockRejectedValue(new Error("403"));
    const user = userEvent.setup();
    render(<RestartButton kind="unit" name="a.service" />);
    await user.click(screen.getByRole("button", { name: "Restart a.service" }));
    await user.click(screen.getByRole("button", { name: "Confirm restart" }));
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("403");
    });
  });
});
