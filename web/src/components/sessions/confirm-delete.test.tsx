import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ConfirmDelete } from "./confirm-delete.tsx";

async function flush(ms: number): Promise<void> {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(ms);
  });
}

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("ConfirmDelete", () => {
  it("asks once, showing the count, then sends on the second click", () => {
    const onConfirm = vi.fn();
    render(<ConfirmDelete count={3} label="Delete selected" onConfirm={onConfirm} />);
    fireEvent.click(screen.getByRole("button", { name: "Delete selected" }));
    expect(onConfirm).not.toHaveBeenCalled();
    const confirm = screen.getByRole("button", { name: "Confirm delete 3?" });
    expect(confirm).toHaveTextContent("3?");
    expect(confirm).toHaveClass("danger");
    fireEvent.click(confirm);
    expect(onConfirm).toHaveBeenCalledOnce();
    // Sent: back to the idle button, so a third click asks again.
    expect(screen.getByRole("button", { name: "Delete selected" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Confirm delete 3?" })).toBeNull();
  });

  it("disarms itself after five seconds", async () => {
    const onConfirm = vi.fn();
    render(<ConfirmDelete count={1} label="Delete alpha" onConfirm={onConfirm} />);
    fireEvent.click(screen.getByRole("button", { name: "Delete alpha" }));
    await flush(4900);
    expect(screen.getByRole("button", { name: "Confirm delete 1?" })).toBeInTheDocument();
    await flush(200);
    expect(screen.queryByRole("button", { name: "Confirm delete 1?" })).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Delete alpha" }));
    expect(onConfirm).not.toHaveBeenCalled();
  });

  it("honours disabled", () => {
    render(
      <ConfirmDelete count={1} isDisabled label="Delete alpha" onConfirm={vi.fn()} />,
    );
    expect(screen.getByRole("button", { name: "Delete alpha" })).toBeDisabled();
  });
});
