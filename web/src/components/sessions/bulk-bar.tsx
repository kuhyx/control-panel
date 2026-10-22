import { useState } from "react";

import type { MutationResult } from "../../lib/types.ts";

import {
  deleteSessions,
  markSessions,
  resumeSessions,
  type SessionEntry,
} from "../../lib/sessions-api.ts";
import { MutationOutcome } from "../tighten-curfew.tsx";
import { ConfirmDelete } from "./confirm-delete.tsx";

// More terminals than this at once is a mistake, not a workflow; the server
// refuses it too.
const MAX_RESUME = 5;

// The sticky bar over the table while rows are selected. One request per
// action for the whole selection; the server's answer is shown here. Success
// refetches and clears the selection (the answer stays until dismissed);
// a refusal or failure keeps the selection so it can be retried or trimmed.
export function BulkBar({
  onChanged,
  onClear,
  selected,
}: Readonly<{
  onChanged: () => void;
  onClear: () => void;
  selected: readonly SessionEntry[];
}>): null | React.JSX.Element {
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<MutationResult | null>(null);
  const [error, setError] = useState<null | string>(null);
  const [copied, setCopied] = useState("");
  const count = selected.length;
  if (count === 0 && result === null && error === null && copied === "") return null;
  const ids = selected.map((s) => s.id);

  const forget = (): void => {
    setResult(null);
    setError(null);
    setCopied("");
  };

  const send = async (call: () => Promise<MutationResult>): Promise<void> => {
    setBusy(true);
    forget();
    try {
      const answer = await call();
      setResult(answer);
      if (answer.ok) {
        onClear();
        onChanged();
      }
    } catch (error_: unknown) {
      setError(String(error_));
    } finally {
      setBusy(false);
    }
  };

  const copy = async (): Promise<void> => {
    try {
      await navigator.clipboard.writeText(selected.map((s) => s.resume_command).join("\n"));
      setCopied(`Copied ${String(count)} command${count === 1 ? "" : "s"}`);
    } catch {
      setCopied("Copy failed");
    }
  };

  const isTooMany = count > MAX_RESUME;
  return (
    <section aria-label="Bulk actions" className="bulk-bar">
      {count > 0 && (
        <>
          <strong>{count} selected</strong>
          <button disabled={busy} onClick={() => void send(() => markSessions(ids, "done"))} type="button">
            Mark done
          </button>
          <button
            className="quiet"
            disabled={busy}
            onClick={() => void send(() => markSessions(ids, null))}
            type="button"
          >
            Unmark
          </button>
          <button className="quiet" onClick={() => void copy()} type="button">
            Copy commands
          </button>
          <button
            className="quiet"
            disabled={busy || isTooMany}
            onClick={() => void send(() => resumeSessions(ids))}
            title={isTooMany ? "max 5 terminals at once" : undefined}
            type="button"
          >
            Resume
          </button>
          <ConfirmDelete
            count={count}
            isDisabled={busy}
            label="Delete"
            onConfirm={() => void send(() => deleteSessions(ids))}
          />
        </>
      )}
      <button
        className="quiet"
        onClick={() => {
          forget();
          onClear();
        }}
        type="button"
      >
        {count > 0 ? "Clear selection" : "Dismiss"}
      </button>
      {copied !== "" && <span className="category">{copied}</span>}
      {error !== null && (
        <span className="empty" role="alert">
          {error}
        </span>
      )}
      {result !== null && <MutationOutcome result={result} />}
    </section>
  );
}
