import type { SubsystemStatus } from "../lib/types.ts";

import { requiresAttention, severityRank } from "../lib/arming.ts";
import { StateBadge } from "./state-badge.tsx";

export function FleetTable({
  subsystems,
}: Readonly<{
  subsystems: readonly SubsystemStatus[];
}>): React.JSX.Element {
  // Worst first, then declared order. Something that is not firing should
  // never be below something that is.
  const sorted = subsystems.toSorted((a, b) => severityRank(a.state) - severityRank(b.state));
  return (
    <table className="table">
      <caption className="sr-only">Every declared subsystem</caption>
      <thead>
        <tr>
          <th scope="col">Subsystem</th>
          <th scope="col">State</th>
          <th scope="col">Units</th>
          <th scope="col">Why</th>
        </tr>
      </thead>
      <tbody>
        {sorted.map((subsystem) => {
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
            <td className="reason">{subsystem.reason}</td>
          </tr>
          );
        })}
      </tbody>
    </table>
  );
}
