import { act, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { usePoll } from "./use-poll.ts";

function Probe({
  load,
}: Readonly<{ load: (signal: AbortSignal) => Promise<string> }>): React.JSX.Element {
  const { error, reload, value } = usePoll(load, 1000);
  return (
    <>
      <p>value:{value ?? "none"}</p>
      <p>error:{error ?? "none"}</p>
      <button onClick={reload} type="button">
        reload
      </button>
    </>
  );
}

function setHidden(isHidden: boolean): void {
  Object.defineProperty(document, "visibilityState", {
    configurable: true,
    get: () => (isHidden ? "hidden" : "visible"),
  });
  document.dispatchEvent(new Event("visibilitychange"));
}

async function flush(ms = 0): Promise<void> {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(ms);
  });
}

afterEach(() => {
  setHidden(false);
  vi.useRealTimers();
});

describe("usePoll", () => {
  it("refetches on the interval, pauses while hidden, catches up when shown", async () => {
    vi.useFakeTimers();
    let n = 0;
    const load = vi.fn(() => {
      n += 1;
      return Promise.resolve(`v${String(n)}`);
    });
    render(<Probe load={load} />);
    await flush();
    expect(screen.getByText("value:v1")).toBeInTheDocument();
    await flush(1000);
    expect(screen.getByText("value:v2")).toBeInTheDocument();
    setHidden(true);
    await flush(3000);
    expect(load).toHaveBeenCalledTimes(2);
    setHidden(false);
    await flush();
    expect(screen.getByText("value:v3")).toBeInTheDocument();
    act(() => {
      screen.getByRole("button", { name: "reload" }).click();
    });
    await flush();
    expect(screen.getByText("value:v4")).toBeInTheDocument();
  });

  it("keeps the last good value when a refresh fails, and clears the error after", async () => {
    vi.useFakeTimers();
    const load = vi
      .fn<() => Promise<string>>()
      .mockResolvedValueOnce("good")
      .mockRejectedValueOnce(new Error("boom"))
      .mockResolvedValue("better");
    render(<Probe load={load} />);
    await flush();
    await flush(1000);
    expect(screen.getByText("value:good")).toBeInTheDocument();
    expect(screen.getByText("error:Error: boom")).toBeInTheDocument();
    await flush(1000);
    expect(screen.getByText("value:better")).toBeInTheDocument();
    expect(screen.getByText("error:none")).toBeInTheDocument();
  });

  it("does not report a read aborted by unmounting", async () => {
    vi.useFakeTimers();
    const spy = vi.spyOn(console, "error");
    const load = vi.fn(
      (signal: AbortSignal) => {
        return new Promise<string>((_resolve, reject) => {
          signal.addEventListener("abort", () => {
            reject(new Error("aborted"));
          });
        });
      },
    );
    const { unmount } = render(<Probe load={load} />);
    unmount();
    await flush(5000);
    expect(load).toHaveBeenCalledOnce();
    expect(spy).not.toHaveBeenCalled();
  });
});
