import { useEffect, useState } from "react";

export interface AsyncState<T> {
  error: null | string;
  value: null | T;
}

// Run `load` whenever `key` changes; abort the previous request on change or
// unmount, and never report an aborted request as an error.
export function useAsync<T>(
  load: (signal: AbortSignal) => Promise<T>,
  key: string,
): AsyncState<T> {
  const [state, setState] = useState<AsyncState<T>>({
    error: null,
    value: null,
  });
  useEffect(() => {
    const controller = new AbortController();
    const run = async (): Promise<void> => {
      try {
        const value = await load(controller.signal);
        setState({ error: null, value });
      } catch (error_: unknown) {
        if (!controller.signal.aborted)
          setState({ error: String(error_), value: null });
      }
    };
    void run();
    return () => {
      controller.abort();
    };
    // `load` is rebuilt every render; `key` is what identifies the request.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);
  return state;
}
