import { useState } from "react";

import type { UnitRecord } from "../lib/types.ts";

import { formatEpochMicros } from "../lib/format.ts";
import { JournalPanel } from "./journal-panel.tsx";
import { LogsToggle } from "./logs-toggle.tsx";
import { RestartButton } from "./restart-button.tsx";
import { StateBadge } from "./state-badge.tsx";

const COLUMNS = 6;

export function UnitTable({
  units,
}: Readonly<{
  units: readonly UnitRecord[];
}>): React.JSX.Element {
  if (units.length === 0) {
    return (
      <p className="empty">
        No systemd units — this subsystem is enforced by another mechanism
        (a binary wrapper, a pacman hook, a file guard, or a container).
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
          <th scope="col">Actions</th>
        </tr>
      </thead>
      <tbody>
        {units.map((unit) => <UnitRow key={`${unit.scope}/${unit.name}`} unit={unit} />)}
      </tbody>
    </table>
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
          <td colSpan={COLUMNS}>
            <JournalPanel name={unit.name} source={unit.scope} />
          </td>
        </tr>
      )}
    </>
  );
}
