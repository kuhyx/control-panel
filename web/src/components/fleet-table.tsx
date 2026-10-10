import type { ColumnSpec } from "../lib/table-state.ts";
import type { SubsystemStatus } from "../lib/types.ts";

import { requiresAttention, severityRank } from "../lib/arming.ts";
import { useTableView } from "../lib/table-state.ts";
import { DashboardLinks } from "./dashboard-links.tsx";
import { StateBadge } from "./state-badge.tsx";
import { ColumnHeader, NoMatchRow, TableHint } from "./table-controls.tsx";

const COLUMNS: readonly ColumnSpec<SubsystemStatus>[] = [
  {
    id: "subsystem",
    label: "Subsystem",
    search: true,
    sortKey: (s) => s.title.toLowerCase(),
    text: (s) => `${s.title} ${s.category}`,
  },
  {
    filter: true,
    id: "state",
    label: "State",
    sortKey: (s) => severityRank(s.state),
    text: (s) => s.state,
  },
  {
    id: "units",
    label: "Units",
    search: true,
    sortKey: (s) => s.units.length,
    text: (s) => String(s.units.length),
  },
  {
    id: "dashboards",
    label: "Dashboards",
    search: true,
    text: (s) => s.dashboards.map((d) => d.label).join(" "),
  },
  { filter: true, id: "why", label: "Why", text: (s) => s.reason },
];

export function FleetTable({
  subsystems,
}: Readonly<{
  subsystems: readonly SubsystemStatus[];
}>): React.JSX.Element {
  // Worst first, then declared order, until a header is clicked. Something
  // that is not firing should never be below something that is.
  const ordered = subsystems.toSorted((a, b) => severityRank(a.state) - severityRank(b.state));
  const view = useTableView("fleet", COLUMNS, ordered);
  return (
    <>
      <TableHint view={view} />
      <table className="table">
        <caption className="sr-only">Every declared subsystem</caption>
        <thead>
          <tr>
            {COLUMNS.map((column) => {
              return (
                <ColumnHeader column={column} key={column.id} view={view} />
              );
            })}
          </tr>
        </thead>
        <tbody>
          {view.rows.length === 0 && <NoMatchRow colSpan={COLUMNS.length} />}
          {view.rows.map((subsystem) => {
            return (
              <tr
                className={requiresAttention(subsystem.state) ? "row-attention" : ""}
                key={subsystem.id}
              >
                <th scope="row">
                  <a href={`#/s/${subsystem.id}`}>{subsystem.title}</a>
                  <span className="category">{subsystem.category}</span>
                </th>
                <td>
                  <StateBadge state={subsystem.state} />
                </td>
                <td className="numeric">{subsystem.units.length}</td>
                <td>
                  <DashboardLinks dashboards={subsystem.dashboards} />
                </td>
                <td className="reason">{subsystem.reason}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </>
  );
}
