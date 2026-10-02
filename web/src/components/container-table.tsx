import { useState } from "react";

import type { ContainerRecord } from "../lib/types.ts";

import { JournalPanel } from "./journal-panel.tsx";
import { LogsToggle } from "./logs-toggle.tsx";
import { RestartButton } from "./restart-button.tsx";
import { StateBadge } from "./state-badge.tsx";

const COLUMNS = 4;

export function ContainerTable({
  containers,
}: Readonly<{
  containers: readonly ContainerRecord[];
}>): React.JSX.Element {
  return (
    <table className="table">
      <caption className="sr-only">Docker containers</caption>
      <thead>
        <tr>
          <th scope="col">Container</th>
          <th scope="col">State</th>
          <th scope="col">Status</th>
          <th scope="col">Actions</th>
        </tr>
      </thead>
      <tbody>
        {containers.map((container) => <ContainerRow container={container} key={container.name} />)}
      </tbody>
    </table>
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
          <td colSpan={COLUMNS}>
            <JournalPanel name={container.name} source="docker" />
          </td>
        </tr>
      )}
    </>
  );
}
