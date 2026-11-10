import type { ColumnSpec } from "../lib/table-state.ts";
import type { SubsystemStatus } from "../lib/types.ts";

import { requiresAttention, severityRank } from "../lib/arming.ts";
import { armingGlyph, CATEGORY_GLYPH, GLYPH } from "../lib/glyphs.ts";
import { useTableView } from "../lib/table-state.ts";
import { DashboardLinks } from "./dashboard-links.tsx";
import { Glyph } from "./glyph.tsx";
import { StateBadge } from "./state-badge.tsx";
import { ColumnHeader, NoMatchRow, TableHint } from "./table-controls.tsx";

const COLUMNS: readonly ColumnSpec<SubsystemStatus>[] = [
  {
    glyph: GLYPH.subsystem,
    id: "subsystem",
    label: "Subsystem",
    search: true,
    sortKey: (s) => s.title.toLowerCase(),
    text: (s) => `${s.title} ${s.category}`,
  },
  {
    filter: true,
    glyph: GLYPH.state,
    id: "state",
    label: "State",
    optionGlyph: armingGlyph,
    sortKey: (s) => severityRank(s.state),
    text: (s) => s.state,
  },
  {
    glyph: GLYPH.units,
    id: "units",
    label: "Units",
    search: true,
    sortKey: (s) => s.units.length,
    text: (s) => String(s.units.length),
  },
  // No Why column: its server-built sentence ("all 7 declared unit(s)
  // armed", "down: …") repeated the badge, the unit count and the dashboard
  // dots; the detail page lists the units that are not armed.
  {
    glyph: GLYPH.dashboards,
    id: "dashboards",
    label: "Dashboards",
    search: true,
    text: (s) => s.dashboards.map((d) => d.label).join(" "),
  },
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
      <table aria-label="Every declared subsystem" className="table">
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
                  <span className="category">
                    <Glyph
                      glyph={CATEGORY_GLYPH[subsystem.category]}
                      label={subsystem.category}
                    />
                  </span>
                </th>
                <td>
                  <StateBadge state={subsystem.state} />
                </td>
                <td className="numeric">{subsystem.units.length}</td>
                <td>
                  <DashboardLinks dashboards={subsystem.dashboards} />
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </>
  );
}
