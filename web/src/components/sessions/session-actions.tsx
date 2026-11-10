import { useState } from "react";

import type { MutationResult } from "../../lib/types.ts";

import { GLYPH } from "../../lib/glyphs.ts";
import {
  deleteSession,
  markSessions,
  resumeSessions,
  type SessionEntry,
} from "../../lib/sessions-api.ts";
import { ErrorNote } from "../error-note.tsx";
import { MutationOutcome } from "../tighten-curfew.tsx";
import { ConfirmDelete } from "./confirm-delete.tsx";
import { COPIED, COPY_FAILED, CopyNote } from "./copy-note.tsx";

// Which mark a click would send, or undefined for no button. Only a manual
// mark can be undone: a session that reported DONE itself has nothing to
// unmark, and re-marking it would change nothing.
function nextMark(session: SessionEntry): "done" | null | undefined {
  if (session.manual_mark === "done") return null;
  return session.done ? undefined : "done";
}

// Resume / Copy / Mark done / Delete for one session. The server decides what
// resuming means (it opens a terminal); its answer is shown verbatim.
export function SessionActions({
  onChanged,
  session,
}: Readonly<{ onChanged: () => void; session: SessionEntry }>): React.JSX.Element {
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<MutationResult | null>(null);
  const [error, setError] = useState<null | string>(null);
  const [copied, setCopied] = useState("");
  const mark = nextMark(session);

  const send = async (
    call: () => Promise<MutationResult>,
    isChange: boolean,
  ): Promise<void> => {
    setBusy(true);
    try {
      setResult(await call());
      setError(null);
      if (isChange) onChanged();
    } catch (error_: unknown) {
      setError(String(error_));
    } finally {
      setBusy(false);
    }
  };

  const copy = async (): Promise<void> => {
    try {
      await navigator.clipboard.writeText(session.resume_command);
      setCopied(COPIED);
    } catch {
      setCopied(COPY_FAILED);
    }
  };

  return (
    <div className="session-actions">
      <button
        aria-label={`Resume ${session.id}`}
        disabled={busy}
        onClick={() => void send(() => resumeSessions([session.id]), false)}
        type="button"
      >
        {GLYPH.resume}
      </button>
      <button
        aria-label={`Copy resume command for ${session.id}`}
        className="quiet"
        onClick={() => void copy()}
        type="button"
      >
        {GLYPH.copy}
      </button>
      {mark !== undefined && (
        <button
          aria-label={mark === null ? `Unmark ${session.id}` : `Mark ${session.id} done`}
          className="quiet"
          disabled={busy}
          onClick={() => void send(() => markSessions([session.id], mark), true)}
          type="button"
        >
          {mark === null ? GLYPH.undo : GLYPH.mark}
        </button>
      )}
      <ConfirmDelete
        count={1}
        isDisabled={busy}
        label={`Delete ${session.id}`}
        onConfirm={() => void send(() => deleteSession(session.id), true)}
      />
      {copied !== "" && <CopyNote copied={copied} />}
      {error !== null && <ErrorNote error={error} />}
      {result !== null && <MutationOutcome result={result} />}
    </div>
  );
}
