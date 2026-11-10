import { useEffect, useState } from "react";

import type { UnknownReport } from "../lib/types.ts";

import { fetchUnknown } from "../lib/api.ts";
import { GLYPH } from "../lib/glyphs.ts";
import { ErrorNote } from "./error-note.tsx";
import { ListenerTable, UserUnitTable } from "./unknown-tables.tsx";

// The manifest only knows what someone remembered to declare. This section is
// the other half: listening ports and user units nothing above accounts for.
// Read once per visit rather than polled -- it changes when a server is started
// by hand, not every five seconds.
export function UnknownSection(): React.JSX.Element {
  const [report, setReport] = useState<null | UnknownReport>(null);
  const [error, setError] = useState<null | string>(null);

  useEffect(() => {
    const controller = new AbortController();
    const read = async (): Promise<void> => {
      try {
        setReport(await fetchUnknown(controller.signal));
      } catch (error_: unknown) {
        if (!controller.signal.aborted) setError(String(error_));
      }
    };
    void read();
    return () => {
      controller.abort();
    };
  }, []);

  return (
    <section aria-label="Not in the manifest" className="card unknown">
      <h2 aria-label="Not in the manifest">🗃</h2>
      {error !== null && <ErrorNote error={error} />}
      {report === null && error === null && (
        <progress aria-label="Looking for undeclared listeners…" />
      )}
      {report !== null && <UnknownBody report={report} />}
    </section>
  );
}

function UnknownBody({
  report,
}: Readonly<{ report: UnknownReport }>): React.JSX.Element {
  if (report.listeners.length === 0 && report.units.length === 0) {
    return (
      <p
        aria-label="Every listening port and user unit is declared"
        className="empty"
        role="status"
      >
        {GLYPH.ok}
      </p>
    );
  }
  return (
    <>
      {report.listeners.length > 0 && (
        <>
          <h3 aria-label="Listening ports">🌐</h3>
          <ListenerTable listeners={report.listeners} />
        </>
      )}
      {report.units.length > 0 && (
        <>
          <h3 aria-label="User units">👤</h3>
          <UserUnitTable units={report.units} />
        </>
      )}
    </>
  );
}
