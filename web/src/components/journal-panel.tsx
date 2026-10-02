import { useEffect, useState } from "react";

import type { JournalSource, JournalTail } from "../lib/types.ts";

import { fetchJournal } from "../lib/api.ts";

export const JOURNAL_LINES = 100;

export function JournalPanel({
  name,
  source,
}: Readonly<{ name: string; source: JournalSource }>): React.JSX.Element {
  const [tail, setTail] = useState<JournalTail | null>(null);
  const [error, setError] = useState<null | string>(null);

  useEffect(() => {
    const controller = new AbortController();
    const read = async (): Promise<void> => {
      try {
        setTail(
          await fetchJournal(source, name, JOURNAL_LINES, controller.signal),
        );
      } catch (error_: unknown) {
        // An abort is this panel closing, not a fault worth showing.
        if (!controller.signal.aborted) setError(String(error_));
      }
    };
    void read();
    return () => {
      controller.abort();
    };
  }, [name, source]);

  if (error !== null) return <p className="empty">{error}</p>;
  return tail === null ? <p className="empty">Reading {name}…</p> : <JournalBody tail={tail} />;
}

export function JournalBody({
  tail,
}: Readonly<{ tail: JournalTail }>): React.JSX.Element {
  return (
    <>
      <p className="category">
        last {String(tail.lines.length)} line(s) of {tail.source}/{tail.name}
      </p>
      {!tail.ok && (
        <p className="empty" role="alert">
          {tail.error === "" ? "the read failed" : tail.error}
        </p>
      )}
      <pre className="log">{tail.lines.join("\n")}</pre>
    </>
  );
}
