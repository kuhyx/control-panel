import type { ColumnSpec } from "../lib/table-state.ts";
import type { Listener, UndeclaredUnit } from "../lib/types.ts";

import { useTableView } from "../lib/table-state.ts";
import { ColumnHeader, NoMatchRow, TableHint } from "./table-controls.tsx";

const NO_PROCESS = "process not visible to this user";

const LISTENER_COLUMNS: readonly ColumnSpec<Listener>[] = [
  {
    id: "listener",
    label: "Listener",
    search: true,
    sortKey: (l) => l.port,
    text: (l) => `${l.address}:${String(l.port)}`,
  },
  {
    id: "process",
    label: "Process",
    search: true,
    text: (l) => (l.process === "" ? NO_PROCESS : l.process),
  },
];

const UNIT_COLUMNS: readonly ColumnSpec<UndeclaredUnit>[] = [
  { id: "unit", label: "Unit", search: true, text: (u) => u.name },
  { filter: true, id: "scope", label: "Scope", text: (u) => u.scope },
];

export function ListenerTable({
  listeners,
}: Readonly<{ listeners: readonly Listener[] }>): React.JSX.Element {
  const view = useTableView("ports", LISTENER_COLUMNS, listeners);
  return (
    <>
      <TableHint view={view} />
      <table className="table">
        <caption className="sr-only">Listening ports not in the manifest</caption>
        <thead>
          <tr>
            {LISTENER_COLUMNS.map((column) => {
              return (
                <ColumnHeader column={column} key={column.id} view={view} />
              );
            })}
          </tr>
        </thead>
        <tbody>
          {view.rows.length === 0 && <NoMatchRow colSpan={LISTENER_COLUMNS.length} />}
          {view.rows.map((listener) => {
            return (
            <tr key={`${listener.address}:${String(listener.port)}`}>
              <th scope="row">
                <code>
                  {listener.address}:{listener.port}
                </code>
              </th>
              <td className="reason">
                {listener.process === "" ? NO_PROCESS : listener.process}
              </td>
            </tr>
            );
          })}
        </tbody>
      </table>
    </>
  );
}

export function UserUnitTable({
  units,
}: Readonly<{ units: readonly UndeclaredUnit[] }>): React.JSX.Element {
  const view = useTableView("userunits", UNIT_COLUMNS, units);
  return (
    <>
      <TableHint view={view} />
      <table className="table">
        <caption className="sr-only">User units not in the manifest</caption>
        <thead>
          <tr>
            {UNIT_COLUMNS.map((column) => {
              return (
                <ColumnHeader column={column} key={column.id} view={view} />
              );
            })}
          </tr>
        </thead>
        <tbody>
          {view.rows.length === 0 && <NoMatchRow colSpan={UNIT_COLUMNS.length} />}
          {view.rows.map((unit) => {
            return (
            <tr key={unit.name}>
              <th scope="row">
                <code>{unit.name}</code>
              </th>
              <td className="reason">{unit.scope}</td>
            </tr>
            );
          })}
        </tbody>
      </table>
    </>
  );
}
