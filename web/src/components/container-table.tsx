import { useState } from "react";

import type { ColumnSpec } from "../lib/table-state.ts";
import type { ContainerRecord } from "../lib/types.ts";

import { severityRank } from "../lib/arming.ts";
import { armingGlyph, GLYPH, SCOPE_GLYPH } from "../lib/glyphs.ts";
import { useTableView } from "../lib/table-state.ts";
import { Glyph } from "./glyph.tsx";
import { JournalPanel } from "./journal-panel.tsx";
import { LogsToggle } from "./logs-toggle.tsx";
import { RestartButton } from "./restart-button.tsx";
import { StateBadge } from "./state-badge.tsx";
import { ColumnHeader, NoMatchRow, TableHint } from "./table-controls.tsx";

const COLUMN_COUNT = 3;

// No Status column: Docker's "Up 4 days (healthy)" is a sentence; the badge
// carries the verdict (the state word is spoken on it).
const COLUMNS: readonly ColumnSpec<ContainerRecord>[] = [
  {
    glyph: GLYPH.containers,
    id: "container",
    label: "Container",
    search: true,
    text: (c) => c.name,
  },
  {
    filter: true,
    glyph: GLYPH.state,
    id: "state",
    label: "State",
    optionGlyph: armingGlyph,
    sortKey: (c) => severityRank(c.arming),
    text: (c) => c.arming,
  },
];

export function ContainerTable({
  containers,
}: Readonly<{
  containers: readonly ContainerRecord[];
}>): React.JSX.Element {
  const view = useTableView("containers", COLUMNS, containers);
  return (
    <>
      <TableHint view={view} />
      <table aria-label="Docker containers" className="table">
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
          {view.rows.map((container) => <ContainerRow container={container} key={container.name} />)}
        </tbody>
      </table>
    </>
  );
}

function ContainerRow({
  container,
}: Readonly<{ container: ContainerRecord }>): React.JSX.Element {
  const [open, setOpen] = useState(false);
  return (
    <>
      <tr>
        <th scope="row">
          {container.name}
          <span className="category">
            <Glyph glyph={SCOPE_GLYPH.docker} label="docker" />
          </span>
        </th>
        <td>
          <StateBadge state={container.arming} />
        </td>
        <td className="actions">
          {container.restartable && (
            <RestartButton kind="container" name={container.name} />
          )}
          <LogsToggle
            name={container.name}
            onToggle={() => {
              setOpen(!open);
            }}
            open={open}
          />
        </td>
      </tr>
      {open && (
        <tr className="log-row">
          <td colSpan={COLUMN_COUNT}>
            <JournalPanel name={container.name} source="docker" />
          </td>
        </tr>
      )}
    </>
  );
}
