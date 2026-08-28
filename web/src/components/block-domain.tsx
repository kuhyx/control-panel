import { useState } from "react";

import type { MutationResult } from "../lib/types.ts";

import { mutate } from "../lib/api.ts";
import { MutationOutcome } from "./tighten-curfew.tsx";

const MIN_REASON = 10;

// Add-only, and not because this form says so: hosts-blocker's protection
// check diffs the entry set against a root-owned immutable state file and
// aborts the install if anything disappeared. There is no remove button
// because there is no remove path that would survive.
export function BlockDomain(): React.JSX.Element {
  const [domain, setDomain] = useState("");
  const [why, setWhy] = useState("");
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<MutationResult | null>(null);
  const [error, setError] = useState<null | string>(null);

  const isReady = domain.trim() !== "" && why.trim().length >= MIN_REASON;

  const submit = async (): Promise<void> => {
    setBusy(true);
    setConfirming(false);
    try {
      setResult(await mutate("hosts-add", { domain, why }));
      setError(null);
    } catch (error_: unknown) {
      setError(String(error_));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section aria-label="Block a domain" className="mutate">
      <p className="reason">
        Adds one entry to the blocklist and rebuilds <code>/etc/hosts</code>.
        There is no way to remove one from here: the installer refuses any
        change that drops an existing entry. The reason is stored beside the
        entry in a comment the guard ignores, so it survives without weakening
        the check.
      </p>

      <div className="fields">
        <label>
          Domain
          <input
            onChange={(event) => {
              setDomain(event.target.value);
            }}
            placeholder="example.com"
            type="text"
            value={domain}
          />
        </label>
        <label className="grow">
          Why (kept with the entry)
          <input
            onChange={(event) => {
              setWhy(event.target.value);
            }}
            placeholder="eats an hour every evening"
            type="text"
            value={why}
          />
        </label>
      </div>

      {confirming ? (
        <p className="confirm">
          Block {domain} permanently? Rebuilding <code>/etc/hosts</code> takes a
          moment.
          <button disabled={busy} onClick={() => void submit()} type="button">
            Yes, block it
          </button>
          <button
            onClick={() => {
              setConfirming(false);
            }}
            type="button"
          >
            Cancel
          </button>
        </p>
      ) : (
        <button
          disabled={busy || !isReady}
          onClick={() => {
            setConfirming(true);
          }}
          type="button"
        >
          {isReady ? "Block domain…" : `Needs a domain and ${MIN_REASON}+ char reason`}
        </button>
      )}

      {busy && <p className="empty">Rebuilding /etc/hosts…</p>}
      {error !== null && (
        <p className="empty" role="alert">
          {error}
        </p>
      )}
      {result !== null && <MutationOutcome result={result} />}
    </section>
  );
}
