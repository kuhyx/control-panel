import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { MutationResult } from "../lib/types.ts";

import * as api from "../lib/api.ts";
import { BlockDomain } from "./block-domain.tsx";
import { MutationOutcome, TightenCurfew } from "./tighten-curfew.tsx";

function outcome(over: Partial<MutationResult>): MutationResult {
  return {
    argv: [],
    ok: false,
    refused: false,
    stderr: "",
    stdout: "",
    summary: "",
    ...over,
  };
}

describe("MutationOutcome", () => {
  it("colours a refusal as the guard working, not as an error", () => {
    const { container } = render(
      <MutationOutcome
        result={outcome({ refused: true, stderr: "not stricter", summary: "no" })}
      />,
    );
    const dot = container.querySelector(".dot") as HTMLElement;
    expect(dot.style.backgroundColor).toBe("var(--warning)");
    // The script's own words, not a paraphrase.
    expect(screen.getByText("not stricter")).toBeInTheDocument();
  });

  it("colours success and hard failure differently", () => {
    const { container: good } = render(
      <MutationOutcome result={outcome({ ok: true, summary: "done" })} />,
    );
    expect(
      (good.querySelector(".dot") as HTMLElement).style.backgroundColor,
    ).toBe("var(--success)");
    const { container: bad } = render(
      <MutationOutcome result={outcome({ summary: "broken" })} />,
    );
    expect(
      (bad.querySelector(".dot") as HTMLElement).style.backgroundColor,
    ).toBe("var(--danger)");
  });

  it("omits the script output block when there is none", () => {
    render(<MutationOutcome result={outcome({ ok: true, summary: "done" })} />);
    expect(screen.queryByText("what the script said")).not.toBeInTheDocument();
  });
});

describe("TightenCurfew", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("requires a confirmation before sending anything", async () => {
    const spy = vi.spyOn(api, "mutate");
    const user = userEvent.setup();
    render(<TightenCurfew />);
    await user.click(screen.getByRole("button", { name: /Tighten curfew/ }));
    expect(spy).not.toHaveBeenCalled();
    expect(screen.getByText(/cannot be loosened again/)).toBeInTheDocument();
  });

  it("sends the three hours as numbers once confirmed", async () => {
    const spy = vi
      .spyOn(api, "mutate")
      .mockResolvedValue(outcome({ ok: true, summary: "tightened" }));
    const user = userEvent.setup();
    render(<TightenCurfew />);
    await user.click(screen.getByRole("button", { name: /Tighten curfew/ }));
    await user.click(screen.getByRole("button", { name: /Yes, tighten it/ }));
    await waitFor(() => {
      expect(spy).toHaveBeenCalledWith("shutdown-hours", {
        mon_wed_hour: 21,
        morning_end_hour: 5,
        thu_sun_hour: 21,
      });
    });
    expect(screen.getByText("tightened")).toBeInTheDocument();
  });

  it("can be cancelled", async () => {
    const spy = vi.spyOn(api, "mutate");
    const user = userEvent.setup();
    render(<TightenCurfew />);
    await user.click(screen.getByRole("button", { name: /Tighten curfew/ }));
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(spy).not.toHaveBeenCalled();
    expect(
      screen.getByRole("button", { name: /Tighten curfew/ }),
    ).toBeInTheDocument();
  });

  it("edits are reflected in what is sent", async () => {
    const spy = vi
      .spyOn(api, "mutate")
      .mockResolvedValue(outcome({ ok: true, summary: "ok" }));
    const user = userEvent.setup();
    render(<TightenCurfew />);
    const monWed = screen.getByLabelText(/Mon/);
    await user.clear(monWed);
    await user.type(monWed, "19");
    const thuSun = screen.getByLabelText(/Thu/);
    await user.clear(thuSun);
    await user.type(thuSun, "20");
    const morning = screen.getByLabelText(/Morning end/);
    await user.clear(morning);
    await user.type(morning, "7");
    await user.click(screen.getByRole("button", { name: /Tighten curfew/ }));
    await user.click(screen.getByRole("button", { name: /Yes, tighten it/ }));
    await waitFor(() => {
      expect(spy).toHaveBeenCalledWith("shutdown-hours", {
        mon_wed_hour: 19,
        morning_end_hour: 7,
        thu_sun_hour: 20,
      });
    });
  });

  it("surfaces a transport failure", async () => {
    vi.spyOn(api, "mutate").mockRejectedValue(new Error("server down"));
    const user = userEvent.setup();
    render(<TightenCurfew />);
    await user.click(screen.getByRole("button", { name: /Tighten curfew/ }));
    await user.click(screen.getByRole("button", { name: /Yes, tighten it/ }));
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/server down/);
    });
  });
});

describe("BlockDomain", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("offers no way to remove an entry", () => {
    render(<BlockDomain />);
    expect(screen.queryByRole("button", { name: /remove|unblock/i })).toBeNull();
    expect(screen.getByText(/no way to remove one from here/)).toBeInTheDocument();
  });

  it("stays disabled until there is a domain and a real reason", async () => {
    const user = userEvent.setup();
    render(<BlockDomain />);
    const button = screen.getByRole("button");
    expect(button).toBeDisabled();
    await user.type(screen.getByLabelText("Domain"), "example.com");
    expect(button).toBeDisabled();
    await user.type(screen.getByLabelText(/Why/), "too short");
    expect(button).toBeDisabled();
    await user.type(screen.getByLabelText(/Why/), " but now long enough");
    expect(button).toBeEnabled();
  });

  it("sends the domain and reason after confirmation", async () => {
    const spy = vi
      .spyOn(api, "mutate")
      .mockResolvedValue(outcome({ ok: true, summary: "blocked" }));
    const user = userEvent.setup();
    render(<BlockDomain />);
    await user.type(screen.getByLabelText("Domain"), "example.com");
    await user.type(screen.getByLabelText(/Why/), "eats an hour every evening");
    await user.click(screen.getByRole("button", { name: /Block domain/ }));
    await user.click(screen.getByRole("button", { name: /Yes, block it/ }));
    await waitFor(() => {
      expect(spy).toHaveBeenCalledWith("hosts-add", {
        domain: "example.com",
        why: "eats an hour every evening",
      });
    });
    expect(screen.getByText("blocked")).toBeInTheDocument();
  });

  it("can be cancelled", async () => {
    const spy = vi.spyOn(api, "mutate");
    const user = userEvent.setup();
    render(<BlockDomain />);
    await user.type(screen.getByLabelText("Domain"), "example.com");
    await user.type(screen.getByLabelText(/Why/), "a sufficiently long reason");
    await user.click(screen.getByRole("button", { name: /Block domain/ }));
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(spy).not.toHaveBeenCalled();
  });

  it("surfaces a transport failure", async () => {
    vi.spyOn(api, "mutate").mockRejectedValue(new Error("nope"));
    const user = userEvent.setup();
    render(<BlockDomain />);
    await user.type(screen.getByLabelText("Domain"), "example.com");
    await user.type(screen.getByLabelText(/Why/), "a sufficiently long reason");
    await user.click(screen.getByRole("button", { name: /Block domain/ }));
    await user.click(screen.getByRole("button", { name: /Yes, block it/ }));
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/nope/);
    });
  });
});
