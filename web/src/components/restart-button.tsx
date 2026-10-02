import { useState } from "react";

import type { MutationResult } from "../lib/types.ts";

import { restart } from "../lib/api.ts";
import { MutationOutcome } from "./tighten-curfew.tsx";

// Two clicks, no window.confirm: a native dialog blocks the page and, under i3,
// steals focus. The server decides what may be restarted -- this button is
// only rendered for what the manifest marks restartable, and a forged request
// for anything else is refused there.
export function RestartButton({
  kind,
  name,
}: Readonly<{ kind: "container" | "unit"; name: string }>): React.JSX.Element {
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<MutationResult | null>(null);
  const [error, setError] = useState<null | string>(null);

  const submit = async (): Promise<void> => {
    setBusy(true);
    setConfirming(false);
    try {
      setResult(await restart(kind, name));
      setError(null);
    } catch (error_: unknown) {
      setError(String(error_));
    } finally {
      setBusy(false);
    }
  };

  return (
    <span className="restart">
      {confirming ? (
        <>
          <button onClick={() => void submit()} type="button">
            Confirm restart
          </button>
          <button
            className="quiet"
            onClick={() => {
              setConfirming(false);
            }}
            type="button"
          >
            Cancel
          </button>
        </>
      ) : (
        <button
          aria-label={`Restart ${name}`}
          disabled={busy}
          onClick={() => {
            setConfirming(true);
          }}
          type="button"
        >
          {busy ? "Restarting…" : "Restart"}
        </button>
      )}
      {error !== null && (
        <span className="empty" role="alert">
          {error}
        </span>
      )}
      {result !== null && <MutationOutcome result={result} />}
    </span>
  );
}
