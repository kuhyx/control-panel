import type { LogReference, SubsystemStatus } from "../lib/types.ts";

import { formatBytes } from "../lib/format.ts";
import { StateBadge } from "./state-badge.tsx";
import { UnitTable } from "./unit-table.tsx";
import { WhyPanel } from "./why-panel.tsx";

function describeLog(log: LogReference): string {
  if (log.kind !== "file") return "journal";
  const size = formatBytes(log.bytes);
  return log.rotated === false ? `${size} · no logrotate entry` : size;
}

export function SubsystemDetail({
  subsystem,
}: Readonly<{
  subsystem: SubsystemStatus;
}>): React.JSX.Element {
  const facts = Object.entries(subsystem.facts);
  return (
    <article className="card">
      <header className="detail-header">
        <h2>{subsystem.title}</h2>
        <StateBadge state={subsystem.state} />
      </header>
      <p className="reason">{subsystem.reason}</p>

      <h3>Units</h3>
      <UnitTable units={subsystem.units} />

      <h3>Why this is enforced</h3>
      <WhyPanel id={subsystem.id} />

      {facts.length > 0 && (
        <>
          <h3>Notes</h3>
          <dl className="facts">
            {facts.map(([key, value]) => {
              return (
              <div className="fact" key={key}>
                <dt>{key}</dt>
                <dd>{String(value)}</dd>
              </div>
              );
            })}
          </dl>
        </>
      )}

      {subsystem.logs.length > 0 && (
        <>
          <h3>Logs</h3>
          <ul className="logs">
            {subsystem.logs.map((log) => {
              return (
              <li key={log.id}>
                <a href={`#/logs/${log.id}`}>{log.path ?? log.unit}</a>
                <span className="category">{describeLog(log)}</span>
              </li>
              );
            })}
          </ul>
        </>
      )}
    </article>
  );
}
