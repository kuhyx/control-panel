import { useState } from "react";

import type { SessionEntry } from "../../lib/sessions-api.ts";
import type { SessionColumn } from "../../lib/sessions-query.ts";
import type { SortState } from "../../lib/table-state.ts";
import type { Selection } from "./use-selection.ts";

import { GLYPH } from "../../lib/glyphs.ts";
import { SessionsHead } from "./sessions-head.tsx";
import { COLUMNS, SessionRows } from "./sessions-row.tsx";

// Rows keyed by session id, and the open set held here (the table stays
// mounted across refetches), so a refresh keeps expanded rows and each row's
// last action result. The selection lives in the page, beside the bulk bar.
export function SessionsTable({
  nowMs,
  onChanged,
  onSort,
  selection,
  sessions,
  sort,
}: Readonly<{
  nowMs: number;
  onChanged: () => void;
  onSort: (column: SessionColumn) => void;
  selection: Selection;
  sessions: readonly SessionEntry[];
  sort: null | SortState;
}>): React.JSX.Element {
  const [open, setOpen] = useState<ReadonlySet<string>>(new Set());
  const toggle = (id: string): void => {
    const next = new Set(open);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setOpen(next);
  };
  return (
    <div className="table-scroll">
      <table className="table tokens-table sessions-table">
        <SessionsHead
          allState={selection.allState}
          onSelectAll={selection.setAll}
          onSort={onSort}
          sort={sort}
        />
        <tbody>
          {sessions.map((session) => {
            return (
              <SessionRows
                isOpen={open.has(session.id)}
                isSelected={selection.has(session.id)}
                key={session.id}
                nowMs={nowMs}
                onChanged={onChanged}
                onSelect={(isRange) => {
                  selection.toggle(session.id, isRange);
                }}
                onToggle={() => {
                  toggle(session.id);
                }}
                session={session}
              />
            );
          })}
          {sessions.length === 0 && (
            <tr>
              <td aria-label="No sessions match." className="empty" colSpan={COLUMNS}>
                {GLYPH.none}
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
