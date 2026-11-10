import { useEffect, useState } from "react";

import type { JournalSource, JournalTail } from "../lib/types.ts";

import { fetchJournal } from "../lib/api.ts";
import { GLYPH, SCOPE_GLYPH } from "../lib/glyphs.ts";
import { ErrorNote } from "./error-note.tsx";

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

  if (error !== null) return <ErrorNote error={error} />;
  return tail === null ? (
    <p aria-label={`Reading ${name}`} className="empty" role="status">
      {GLYPH.reading}
    </p>
  ) : (
    <JournalBody tail={tail} />
  );
}

// "≡ 100 · $ name": line count, then the source as its prompt glyph.
export function JournalBody({
  tail,
}: Readonly<{ tail: JournalTail }>): React.JSX.Element {
  return (
    <>
      <p
        aria-label={`last ${String(tail.lines.length)} line(s) of ${tail.source}/${tail.name}`}
        className="category"
      >
        ≡ {tail.lines.length} · <span aria-hidden="true">{SCOPE_GLYPH[tail.source]}</span>{" "}
        {tail.name}
      </p>
      {!tail.ok && <ErrorNote error={tail.error === "" ? "the read failed" : tail.error} />}
      <pre className="log">{tail.lines.join("\n")}</pre>
    </>
  );
}
