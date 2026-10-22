import { useEffect, useEffectEvent, useState } from "react";

export interface PollState<T> {
  error: null | string;
  // Fetch now (e.g. after a mutation) and restart the interval.
  reload: () => void;
  value: null | T;
}

const isHidden = (): boolean => document.visibilityState === "hidden";

// useAsync, but refetched every `intervalMs` while the tab is visible, and
// at once when it becomes visible again. A failed refresh keeps the last good
// value (the error is shown beside it), so a blip never blanks the list.
export function usePoll<T>(
  load: (signal: AbortSignal) => Promise<T>,
  intervalMs: number,
): PollState<T> {
  const [state, setState] = useState<Omit<PollState<T>, "reload">>({
    error: null,
    value: null,
  });
  const [generation, setGeneration] = useState(0);
  // `load` is rebuilt every render; the effect only restarts on reload.
  const fetchNow = useEffectEvent((signal: AbortSignal) => load(signal));

  useEffect(() => {
    const controller = new AbortController();
    const run = async (): Promise<void> => {
      try {
        const value = await fetchNow(controller.signal);
        setState({ error: null, value });
      } catch (error_: unknown) {
        if (!controller.signal.aborted) {
          setState((previous) => ({ error: String(error_), value: previous.value }));
        }
      }
    };
    const runIfVisible = (): void => {
      if (!isHidden()) void run();
    };
    void run();
    const timer = setInterval(runIfVisible, intervalMs);
    document.addEventListener("visibilitychange", runIfVisible);
    return () => {
      controller.abort();
      clearInterval(timer);
      document.removeEventListener("visibilitychange", runIfVisible);
    };
  }, [generation, intervalMs]);

  return {
    ...state,
    reload: () => {
      setGeneration((n) => n + 1);
    },
  };
}
