import type { UnitRecord } from "../lib/types.ts";

import { formatEpochMicros } from "../lib/format.ts";
import { StateBadge } from "./state-badge.tsx";

export function UnitTable({
  units,
}: Readonly<{
  units: readonly UnitRecord[];
}>): React.JSX.Element {
  if (units.length === 0) {
    return (
      <p className="empty">
        No systemd units — this subsystem is enforced by another mechanism
        (a binary wrapper, a pacman hook, or a file guard).
      </p>
    );
  }
  return (
    <table className="table">
      <caption className="sr-only">Declared units</caption>
      <thead>
        <tr>
          <th scope="col">Unit</th>
          <th scope="col">State</th>
          <th scope="col">Unit file</th>
          <th scope="col">Next run</th>
          <th scope="col">Why</th>
        </tr>
      </thead>
      <tbody>
        {units.map((unit) => {
          return (
          <tr key={`${unit.scope}/${unit.name}`}>
            <th scope="row">
              {unit.name}
              <span className="category">{unit.scope}</span>
            </th>
            <td>
              <StateBadge state={unit.arming} />
            </td>
            <td>
              {unit.installed ? (unit.unit_file_state ?? "—") : "not installed"}
              {unit.preset !== null && unit.preset !== unit.unit_file_state && (
                <span className="category">preset {unit.preset}</span>
              )}
            </td>
            <td>{formatEpochMicros(unit.next_elapse)}</td>
            <td className="reason">{unit.arming_reason.join("; ")}</td>
          </tr>
          );
        })}
      </tbody>
    </table>
  );
}
