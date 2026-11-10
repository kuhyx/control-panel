import { useState } from "react";

import type { MutationResult } from "../lib/types.ts";

import { mutate } from "../lib/api.ts";
import { GLYPH } from "../lib/glyphs.ts";
import { ErrorNote } from "./error-note.tsx";
import { MutationOutcome } from "./tighten-curfew.tsx";

const MIN_REASON = 10;
const DOMAIN = "🌐";
const WHY = "✎";
const BLOCK = "🚫";

// Add-only, and not because this form says so: hosts-blocker's protection
// check diffs the entry set against a root-owned immutable state file and
// aborts the install if anything disappeared. There is no remove button
// because there is no remove path that would survive. The reason is stored
// beside the entry in a comment the guard ignores.
export function BlockDomain(): React.JSX.Element {
  const [domain, setDomain] = useState("");
  const [why, setWhy] = useState("");
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<MutationResult | null>(null);
  const [error, setError] = useState<null | string>(null);

  const reasonLength = why.trim().length;
  const isReady = domain.trim() !== "" && reasonLength >= MIN_REASON;

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
      <div className="fields">
        <label>
          <span aria-hidden="true">{DOMAIN}</span>
          <input
            aria-label="Domain"
            onChange={(event) => {
              setDomain(event.target.value);
            }}
            type="text"
            value={domain}
          />
        </label>
        <label className="grow">
          <span aria-hidden="true">{WHY}</span>
          <input
            aria-label="Why (kept with the entry)"
            onChange={(event) => {
              setWhy(event.target.value);
            }}
            type="text"
            value={why}
          />
          {/* The reason needs MIN_REASON characters: a live count shows how
              far it is. */}
          <span
            aria-label={`${String(reasonLength)} of ${String(MIN_REASON)} characters`}
            className="category"
            role="img"
          >
            {Math.min(reasonLength, MIN_REASON)}/{MIN_REASON}
          </span>
        </label>
      </div>

      {confirming ? (
        <p className="confirm">
          {BLOCK} <code>{domain}</code>
          <button
            aria-label="Yes, block it"
            className="danger"
            disabled={busy}
            onClick={() => void submit()}
            type="button"
          >
            {BLOCK}?
          </button>
          <button
            aria-label="Cancel"
            onClick={() => {
              setConfirming(false);
            }}
            type="button"
          >
            {GLYPH.clear}
          </button>
        </p>
      ) : (
        <button
          aria-label="Block domain"
          disabled={busy || !isReady}
          onClick={() => {
            setConfirming(true);
          }}
          type="button"
        >
          {BLOCK}
        </button>
      )}

      {busy && (
        <p aria-label="Rebuilding /etc/hosts" className="empty" role="status">
          {GLYPH.reading}
        </p>
      )}
      {error !== null && <ErrorNote error={error} />}
      {result !== null && <MutationOutcome result={result} />}
    </section>
  );
}
