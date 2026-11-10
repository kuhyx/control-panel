import { useState } from "react";

import type { ColumnSpec } from "../lib/table-state.ts";
import type { UnitRecord } from "../lib/types.ts";

import { severityRank } from "../lib/arming.ts";
import { formatEpochMicros } from "../lib/format.ts";
import { armingGlyph, GLYPH, SCOPE_GLYPH, unitFileGlyph } from "../lib/glyphs.ts";
import { useTableView } from "../lib/table-state.ts";
import { Glyph } from "./glyph.tsx";
import { JournalPanel } from "./journal-panel.tsx";
import { LogsToggle } from "./logs-toggle.tsx";
import { RestartButton } from "./restart-button.tsx";
import { StateBadge } from "./state-badge.tsx";
import { ColumnHeader, NoMatchRow, TableHint } from "./table-controls.tsx";

const COLUMN_COUNT = 5;
const NOT_INSTALLED = "not installed";

// systemd reports next_elapse in microseconds; a unit with no timer has none,
// and a missing value sorts last whichever way the column is ordered.
function nextRunKey(unit: UnitRecord): null | number {
  const micros = Number(unit.state.next_elapse);
  return Number.isFinite(micros) && micros > 0 ? micros : null;
}

function fileState(unit: UnitRecord): string {
  return unit.installed ? (unit.state.unit_file_state ?? "—") : NOT_INSTALLED;
}

function fileGlyph(value: string): string {
  if (value === NOT_INSTALLED) return GLYPH.none;
  return value === "—" ? value : unitFileGlyph(value);
}

// No Why column: arming_reason is a server-built sentence; the badge says
// the verdict and the unit-file glyph the main cause.
const COLUMNS: readonly ColumnSpec<UnitRecord>[] = [
  {
    glyph: GLYPH.units,
    id: "unit",
    label: "Unit",
    search: true,
    text: (u) => `${u.name} ${u.scope}`,
  },
  {
    filter: true,
    glyph: GLYPH.state,
    id: "state",
    label: "State",
    optionGlyph: armingGlyph,
    sortKey: (u) => severityRank(u.arming),
    text: (u) => u.arming,
  },
  {
    filter: true,
    glyph: "📄",
    id: "file",
    label: "Unit file",
    optionGlyph: fileGlyph,
    text: fileState,
  },
  {
    glyph: GLYPH.age,
    id: "next",
    label: "Next run",
    search: true,
    sortKey: nextRunKey,
    text: (u) => formatEpochMicros(u.state.next_elapse),
  },
];

export function UnitTable({
  units,
}: Readonly<{
  units: readonly UnitRecord[];
}>): React.JSX.Element {
  const view = useTableView("units", COLUMNS, units);
  if (units.length === 0) {
    // Enforced by something else: a binary wrapper, a pacman hook, a file
    // guard or a container.
    return (
      <p aria-label="No systemd units" className="empty" role="status">
        {GLYPH.none}
      </p>
    );
  }
  return (
    <>
      <TableHint view={view} />
      <table aria-label="Declared units" className="table">
        <thead>
          <tr>
            {COLUMNS.map((column) => {
              return (
                <ColumnHeader column={column} key={column.id} view={view} />
              );
            })}
            <th scope="col"><span aria-label="Actions">{GLYPH.actions}</span></th>
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

function UnitFile({ unit }: Readonly<{ unit: UnitRecord }>): React.JSX.Element {
  const value = fileState(unit);
  const { preset } = unit.state;
  return (
    <>
      <Glyph glyph={fileGlyph(value)} label={value} />
      {preset !== null && preset !== unit.state.unit_file_state && (
        <span className="category">
          <Glyph glyph={`≠${unitFileGlyph(preset)}`} label={`preset ${preset}`} />
        </span>
      )}
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
          <span className="category">
            <Glyph glyph={SCOPE_GLYPH[unit.scope]} label={unit.scope} />
          </span>
        </th>
        <td>
          <StateBadge state={unit.arming} />
        </td>
        <td>
          <UnitFile unit={unit} />
        </td>
        <td>{formatEpochMicros(unit.state.next_elapse)}</td>
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
