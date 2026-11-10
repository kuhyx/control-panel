import { useState } from "react";

import { GLYPH } from "../../lib/glyphs.ts";
import { fetchSessions } from "../../lib/sessions-api.ts";
import {
  filterSessions,
  sessionsFromSearch,
  type SessionsQuery,
  sessionsToSearch,
  sortSessions,
} from "../../lib/sessions-query.ts";
import { nextSort } from "../../lib/table-query.ts";
import { ErrorNote } from "../error-note.tsx";
import { BulkBar } from "./bulk-bar.tsx";
import { SessionsFilters } from "./sessions-filters.tsx";
import { SessionsTable } from "./sessions-table.tsx";
import { usePoll } from "./use-poll.ts";
import { useSelection } from "./use-selection.ts";

// The scan is cheap (see scan_ms) and sessions change while kuhy works, so
// the list refreshes itself; usePoll pauses it while the tab is hidden.
const POLL_MS = 10_000;
const BASE = "#/sessions";

// Every Claude Code session, the ones waiting on kuhy first (server order,
// until a column sort is picked), finished ones hidden unless asked for.
// Filters and the sort live in the hash query.
export function SessionsPage({
  now = Date.now,
}: Readonly<{ now?: () => number }>): React.JSX.Element {
  const [query, setQuery] = useState<SessionsQuery>(() =>
    sessionsFromSearch(globalThis.location.hash.split("?", 2)[1] ?? ""),
  );
  const { error, reload, value } = usePoll(fetchSessions, POLL_MS);
  const nowMs = now();
  const all = value?.sessions ?? [];
  const rows = sortSessions(filterSessions(all, query, nowMs), query.sort);
  const selection = useSelection(rows);
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
      <h2 aria-label="Sessions" className="page-title">
        {GLYPH.sessions}
      </h2>
      {/* Per-status counts live on the chips; this line keeps the scan's
          size and cost: "🔍 1857 · 12 ms". */}
      {value !== null && (
        <p
          aria-label={`${String(value.scanned)} sessions scanned in ${String(Math.round(value.scan_ms))} ms`}
          className="category"
        >
          {GLYPH.search} {value.scanned} · {Math.round(value.scan_ms)} ms
        </p>
      )}
      <SessionsFilters onQuery={update} query={query} sessions={all} />
      {error !== null && <ErrorNote error={error} />}
      <BulkBar
        onChanged={reload}
        onClear={selection.clear}
        selected={selection.selected}
      />
      {value === null
        ? error === null && (
          <p aria-label="Reading" className="empty" role="status">
            {GLYPH.reading}
          </p>
        )
        : (
          <SessionsTable
            nowMs={nowMs}
            onChanged={reload}
            onSort={(column) => {
              update({ ...query, sort: nextSort(query.sort, column) });
            }}
            selection={selection}
            sessions={rows}
            sort={query.sort}
          />
        )}
    </>
  );
}
