import type { ColumnSpec } from "../lib/table-state.ts";
import type { Listener, UndeclaredUnit } from "../lib/types.ts";

import { GLYPH, scopeGlyph } from "../lib/glyphs.ts";
import { useTableView } from "../lib/table-state.ts";
import { Glyph } from "./glyph.tsx";
import { ColumnHeader, NoMatchRow, TableHint } from "./table-controls.tsx";

// An empty process is one this user may not see (root's sockets): a hidden
// eye, spoken as the old sentence.
const NO_PROCESS = "process not visible to this user";

const LISTENER_COLUMNS: readonly ColumnSpec<Listener>[] = [
  {
    glyph: "🌐",
    id: "listener",
    label: "Listener",
    search: true,
    sortKey: (l) => l.port,
    text: (l) => `${l.address}:${String(l.port)}`,
  },
  {
    glyph: "⚙",
    id: "process",
    label: "Process",
    search: true,
    text: (l) => (l.process === "" ? NO_PROCESS : l.process),
  },
];

const UNIT_COLUMNS: readonly ColumnSpec<UndeclaredUnit>[] = [
  { glyph: GLYPH.units, id: "unit", label: "Unit", search: true, text: (u) => u.name },
  {
    filter: true,
    glyph: "👤",
    id: "scope",
    label: "Scope",
    optionGlyph: scopeGlyph,
    text: (u) => u.scope,
  },
];

export function ListenerTable({
  listeners,
}: Readonly<{ listeners: readonly Listener[] }>): React.JSX.Element {
  const view = useTableView("ports", LISTENER_COLUMNS, listeners);
  return (
    <>
      <TableHint view={view} />
      <table className="table">
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
                {listener.process === "" ? (
                  <Glyph glyph="🙈" label={NO_PROCESS} />
                ) : (
                  listener.process
                )}
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
              <td className="reason">
                <Glyph glyph={scopeGlyph(unit.scope)} label={unit.scope} />
              </td>
            </tr>
            );
          })}
        </tbody>
      </table>
    </>
  );
}
