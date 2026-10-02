import { useEffect, useState } from "react";

import type { UnknownReport } from "../lib/types.ts";

import { fetchUnknown } from "../lib/api.ts";

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
      <h2>Not in the manifest</h2>
      {error !== null && <p className="empty">{error}</p>}
      {report === null && error === null && (
        <p className="empty">Looking for undeclared listeners…</p>
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
      <p className="empty">
        Every listening port and user unit is declared somewhere above.
      </p>
    );
  }
  return (
    <>
      {report.listeners.length > 0 && (
        <>
          <h3>Listening ports</h3>
          <ul className="logs">
            {report.listeners.map((listener) => {
              return (
                <li key={`${listener.address}:${String(listener.port)}`}>
                  <code>
                    {listener.address}:{listener.port}
                  </code>
                  <span className="category">
                    {listener.process === ""
                      ? "process not visible to this user"
                      : listener.process}
                  </span>
                </li>
              );
            })}
          </ul>
        </>
      )}
      {report.units.length > 0 && (
        <>
          <h3>User units</h3>
          <ul className="logs">
            {report.units.map((unit) => {
              return (
                <li key={unit.name}>
                  <code>{unit.name}</code>
                  <span className="category">{unit.scope}</span>
                </li>
              );
            })}
          </ul>
        </>
      )}
    </>
  );
}
