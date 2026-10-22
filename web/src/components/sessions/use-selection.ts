import { useRef, useState } from "react";

import type { SessionEntry } from "../../lib/sessions-api.ts";

export interface Selection {
  // Header checkbox state over the rows shown.
  allState: "all" | "none" | "some";
  clear: () => void;
  has: (id: string) => boolean;
  // The selected rows, in display order: what a bulk action is sent.
  selected: SessionEntry[];
  setAll: (isOn: boolean) => void;
  // Flip one row; with `isRange`, set every row from the last click to this
  // one to this row's new state.
  toggle: (id: string, isRange: boolean) => void;
}

// Ids are stored, but the selection is always derived as "stored ids among
// the rows shown". So it survives the auto-refresh (same ids, new objects),
// an id that vanished from the payload simply drops out, and a bulk action
// (Delete above all) can never reach a row a filter hides or one that turned
// done on a refresh while Show done is off.
export function useSelection(rows: readonly SessionEntry[]): Selection {
  const [ids, setIds] = useState<ReadonlySet<string>>(() => new Set());
  const anchor = useRef<null | string>(null);
  const selected = rows.filter((row) => ids.has(row.id));
  let allState: Selection["allState"] = "some";
  if (selected.length === 0) allState = "none";
  else if (selected.length === rows.length) allState = "all";

  const toggle = (id: string, isRange: boolean): void => {
    const isOn = !ids.has(id);
    const to = rows.findIndex((row) => row.id === id);
    const from = isRange ? rows.findIndex((row) => row.id === anchor.current) : -1;
    const span =
      from === -1
        ? [id]
        : rows.slice(Math.min(from, to), Math.max(from, to) + 1).map((row) => row.id);
    const next = new Set(ids);
    for (const each of span) {
      if (isOn) next.add(each);
      else next.delete(each);
    }
    anchor.current = id;
    setIds(next);
  };

  return {
    allState,
    clear: () => {
      anchor.current = null;
      setIds(new Set());
    },
    has: (id) => ids.has(id),
    selected,
    setAll: (isOn) => {
      anchor.current = null;
      setIds(new Set(isOn ? rows.map((row) => row.id) : []));
    },
    toggle,
  };
}
