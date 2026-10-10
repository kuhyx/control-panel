import { useState } from "react";

import type { ColumnSpec } from "../lib/table-state.ts";
import type { UnitRecord } from "../lib/types.ts";

import { severityRank } from "../lib/arming.ts";
import { formatEpochMicros } from "../lib/format.ts";
import { useTableView } from "../lib/table-state.ts";
import { JournalPanel } from "./journal-panel.tsx";
import { LogsToggle } from "./logs-toggle.tsx";
import { RestartButton } from "./restart-button.tsx";
import { StateBadge } from "./state-badge.tsx";
import { ColumnHeader, NoMatchRow, TableHint } from "./table-controls.tsx";

const COLUMN_COUNT = 6;

// systemd reports next_elapse in microseconds; a unit with no timer has none,
// and a missing value sorts last whichever way the column is ordered.
function nextRunKey(unit: UnitRecord): null | number {
  const micros = Number(unit.state.next_elapse);
  return Number.isFinite(micros) && micros > 0 ? micros : null;
}

const COLUMNS: readonly ColumnSpec<UnitRecord>[] = [
  { id: "unit", label: "Unit", search: true, text: (u) => `${u.name} ${u.scope}` },
  {
    filter: true,
    id: "state",
    label: "State",
    sortKey: (u) => severityRank(u.arming),
    text: (u) => u.arming,
  },
  {
    filter: true,
    id: "file",
    label: "Unit file",
    text: (u) => (u.installed ? (u.state.unit_file_state ?? "—") : "not installed"),
  },
  {
    id: "next",
    label: "Next run",
    search: true,
    sortKey: nextRunKey,
    text: (u) => formatEpochMicros(u.state.next_elapse),
  },
  { filter: true, id: "why", label: "Why", text: (u) => u.arming_reason.join("; ") },
];

export function UnitTable({
  units,
}: Readonly<{
  units: readonly UnitRecord[];
}>): React.JSX.Element {
  const view = useTableView("units", COLUMNS, units);
  if (units.length === 0) {
    return (
      <p className="empty">
        No systemd units — this subsystem is enforced by another mechanism
        (a binary wrapper, a pacman hook, a file guard, or a container).
      </p>
    );
  }
  return (
    <>
      <TableHint view={view} />
      <table className="table">
        <caption className="sr-only">Declared units</caption>
        <thead>
          <tr>
            {COLUMNS.map((column) => {
              return (
                <ColumnHeader column={column} key={column.id} view={view} />
              );
            })}
            <th scope="col">Actions</th>
          </tr>
        </thead>
        <tbody>
          {view.rows.length === 0 && <NoMatchRow colSpan={COLUMN_COUNT} />}
          {view.rows.map((unit) => <UnitRow key={`${unit.scope}/${unit.name}`} unit={unit} />)}
        </tbody>
      </table>
    </>
  );
}

function UnitRow({ unit }: Readonly<{ unit: UnitRecord }>): React.JSX.Element {
  const [open, setOpen] = useState(false);
  return (
    <>
      <tr>
        <th scope="row">
          {unit.name}
          <span className="category">{unit.scope}</span>
        </th>
        <td>
          <StateBadge state={unit.arming} />
        </td>
        <td>
          {unit.installed ? (unit.state.unit_file_state ?? "—") : "not installed"}
          {unit.state.preset !== null &&
            unit.state.preset !== unit.state.unit_file_state && (
              <span className="category">preset {unit.state.preset}</span>
            )}
        </td>
        <td>{formatEpochMicros(unit.state.next_elapse)}</td>
        <td className="reason">{unit.arming_reason.join("; ")}</td>
        <td className="actions">
          {unit.restartable && <RestartButton kind="unit" name={unit.name} />}
          {unit.installed && (
            <LogsToggle
              name={unit.name}
              onToggle={() => {
                setOpen(!open);
              }}
              open={open}
            />
          )}
        </td>
      </tr>
      {open && (
        <tr className="log-row">
          <td colSpan={COLUMN_COUNT}>
            <JournalPanel name={unit.name} source={unit.scope} />
          </td>
        </tr>
      )}
    </>
  );
}
