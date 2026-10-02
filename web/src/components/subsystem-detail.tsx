import type { LogReference, SubsystemStatus } from "../lib/types.ts";

import { formatBytes } from "../lib/format.ts";
import { BlockDomain } from "./block-domain.tsx";
import { ContainerTable } from "./container-table.tsx";
import { DashboardLinks } from "./dashboard-links.tsx";
import { ProbeList } from "./probe-list.tsx";
import { StateBadge } from "./state-badge.tsx";
import { TightenCurfew } from "./tighten-curfew.tsx";
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

      {subsystem.dashboards.length > 0 && (
        <>
          <h3>Dashboards</h3>
          <DashboardLinks dashboards={subsystem.dashboards} detailed />
        </>
      )}

      {subsystem.containers.length > 0 && (
        <>
          <h3>Containers</h3>
          <ContainerTable containers={subsystem.containers} />
        </>
      )}

      {subsystem.probes.length > 0 && (
        <>
          <h3>Probes</h3>
          <ProbeList probes={subsystem.probes} />
        </>
      )}

      <h3>Units</h3>
      <UnitTable units={subsystem.units} />

      <h3>Why this is enforced</h3>
      <WhyPanel id={subsystem.id} />

      {/* Only two subsystems have a writable knob, and both only tighten. */}
      {subsystem.id === "shutdown" && (
        <>
          <h3>Make it stricter</h3>
          <TightenCurfew />
        </>
      )}
      {subsystem.id === "hosts" && (
        <>
          <h3>Make it stricter</h3>
          <BlockDomain />
        </>
      )}

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
