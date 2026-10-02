import { useEffect, useState } from "react";

import type { JournalTail, LogTail } from "../lib/types.ts";

import { fetchLog } from "../lib/api.ts";
import { formatBytes } from "../lib/format.ts";
import { JournalBody } from "./journal-panel.tsx";

const LINES = 200;

// /api/logs/<id> answers a file tail or, for a journal-kind log, the same
// shape /api/journal does. Only the journal shape carries `source`.
function isJournal(tail: JournalTail | LogTail): tail is JournalTail {
  return "source" in tail;
}

export function LogViewer({
  id,
}: Readonly<{ id: string }>): React.JSX.Element {
  const [tail, setTail] = useState<JournalTail | LogTail | null>(null);
  const [error, setError] = useState<null | string>(null);

  useEffect(() => {
    const controller = new AbortController();
    const read = async (): Promise<void> => {
      try {
        setTail(await fetchLog(id, LINES, controller.signal));
      } catch (error_: unknown) {
        // An abort is this component unmounting, not a fault worth showing.
        if (!controller.signal.aborted) setError(String(error_));
      }
    };
    void read();
    return () => {
      controller.abort();
    };
  }, [id]);

  if (error !== null) return <p className="empty">{error}</p>;
  if (tail === null) return <p className="empty">Loading {id}…</p>;

  if (isJournal(tail)) {
    return (
      <article className="card">
        <h2>{tail.name}</h2>
        <JournalBody tail={tail} />
      </article>
    );
  }

  return (
    <article className="card">
      <h2>{tail.path ?? id}</h2>
      <p className="category">
        {tail.truncated
          ? `last ${String(tail.lines.length)} lines of ${formatBytes(tail.total_bytes)} — the file is never read whole`
          : `${String(tail.lines.length)} line(s)`}
      </p>
      {tail.note !== undefined && <p className="empty">{tail.note}</p>}
      <pre className="log">{tail.lines.join("\n")}</pre>
    </article>
  );
}
