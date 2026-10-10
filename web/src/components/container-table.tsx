import { useState } from "react";

import type { ColumnSpec } from "../lib/table-state.ts";
import type { ContainerRecord } from "../lib/types.ts";

import { severityRank } from "../lib/arming.ts";
import { useTableView } from "../lib/table-state.ts";
import { JournalPanel } from "./journal-panel.tsx";
import { LogsToggle } from "./logs-toggle.tsx";
import { RestartButton } from "./restart-button.tsx";
import { StateBadge } from "./state-badge.tsx";
import { ColumnHeader, NoMatchRow, TableHint } from "./table-controls.tsx";

const COLUMN_COUNT = 4;

const COLUMNS: readonly ColumnSpec<ContainerRecord>[] = [
  { id: "container", label: "Container", search: true, text: (c) => c.name },
  {
    filter: true,
    id: "state",
    label: "State",
    sortKey: (c) => severityRank(c.arming),
    text: (c) => c.arming,
  },
  {
    id: "status",
    label: "Status",
    search: true,
    text: (c) => `${c.state} ${c.status}`.trim(),
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
      <table className="table">
        <caption className="sr-only">Docker containers</caption>
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
          <span className="category">docker</span>
        </th>
        <td>
          <StateBadge state={container.arming} />
        </td>
        <td>
          {container.state === "" ? "—" : container.state}
          <span className="category">{container.status}</span>
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
