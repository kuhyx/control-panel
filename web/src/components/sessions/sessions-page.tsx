import { useState } from "react";

import {
  fetchSessions,
  sessionsFromSearch,
  type SessionsQuery,
  sessionsToSearch,
  statusCounts,
  visibleSessions,
} from "../../lib/sessions-api.ts";
import { PageTabs } from "../tokens/page-tabs.tsx";
import { SessionsTable } from "./sessions-table.tsx";
import { usePoll } from "./use-poll.ts";

// The scan is cheap (see scan_ms) and sessions change while kuhy works, so
// the list refreshes itself; usePoll pauses it while the tab is hidden.
const POLL_MS = 10_000;
const BASE = "#/tokens/sessions";

// Every Claude Code session, the ones waiting on kuhy first (server order),
// finished ones hidden unless asked for. Filters live in the hash query.
export function SessionsPage({
  now = Date.now,
}: Readonly<{ now?: () => number }>): React.JSX.Element {
  const [query, setQuery] = useState<SessionsQuery>(() =>
    sessionsFromSearch(globalThis.location.hash.split("?", 2)[1] ?? ""),
  );
  const { error, reload, value } = usePoll(fetchSessions, POLL_MS);
  const update = (next: SessionsQuery): void => {
    setQuery(next);
    const search = sessionsToSearch(next);
    globalThis.history.replaceState(
      null,
      "",
      search === "" ? BASE : `${BASE}?${search}`,
    );
  };
  return (
    <>
      <PageTabs active="sessions" />
      <h2 className="page-title">Claude Code sessions</h2>
      {value !== null && (
        <p className="category">
          {statusCounts(value.sessions)} · {value.scanned} sessions scanned in{" "}
          {Math.round(value.scan_ms)} ms
        </p>
      )}
      <div className="filter-bar">
        <label>
          Filter sessions
          <input
            onChange={(event) => {
              update({ ...query, q: event.target.value });
            }}
            placeholder="project, title or cwd"
            type="search"
            value={query.q}
          />
        </label>
        <label className="check">
          <input
            checked={query.showDone}
            onChange={(event) => {
              update({ ...query, showDone: event.target.checked });
            }}
            type="checkbox"
          />
          Show done
        </label>
      </div>
      {error !== null && (
        <p className="empty" role="alert">
          {error}
        </p>
      )}
      {value === null
        ? error === null && <p className="empty">Reading…</p>
        : (
          <SessionsTable
            nowMs={now()}
            onChanged={reload}
            sessions={visibleSessions(value.sessions, query)}
          />
        )}
    </>
  );
}
