import type { LogReference, SubsystemStatus } from "../lib/types.ts";

import { formatBytes } from "../lib/format.ts";
import { GLYPH } from "../lib/glyphs.ts";
import { BlockDomain } from "./block-domain.tsx";
import { ContainerTable } from "./container-table.tsx";
import { DashboardLinks } from "./dashboard-links.tsx";
import { Glyph } from "./glyph.tsx";
import { ProbeList } from "./probe-list.tsx";
import { StateBadge } from "./state-badge.tsx";
import { TightenCurfew } from "./tighten-curfew.tsx";
import { UnitTable } from "./unit-table.tsx";
import { WhyPanel } from "./why-panel.tsx";

// The aggregator's own prefix; what follows it is the owner's marker text
// (control_panel/_disarm.py), which is shown as written.
const DISARM_PREFIX = "disarmed on purpose: ";

function LogSize({ log }: Readonly<{ log: LogReference }>): React.JSX.Element {
  if (log.kind !== "file") return <Glyph glyph="📓" label="journal" />;
  return (
    <>
      {formatBytes(log.bytes)}
      {log.rotated === false && (
        <>
          {" "}
          <Glyph glyph={GLYPH.error} label="no logrotate entry" />
        </>
      )}
    </>
  );
}

function Heading({
  glyph,
  label,
}: Readonly<{ glyph: string; label: string }>): React.JSX.Element {
  return (
    <h3 aria-label={label}>
      <span aria-hidden="true">{glyph}</span>
    </h3>
  );
}

// The server's reason sentence is not painted (the badge and the tables say
// it); only a deliberate disarm's own note is, since its owner wrote it.
function DisarmNote({
  subsystem,
}: Readonly<{ subsystem: SubsystemStatus }>): null | React.JSX.Element {
  if (!subsystem.reason.startsWith(DISARM_PREFIX)) return null;
  return (
    <p className="reason">
      <Glyph glyph="⏸" label="disarmed on purpose" />{" "}
      {subsystem.reason.slice(DISARM_PREFIX.length)}
    </p>
  );
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
      <DisarmNote subsystem={subsystem} />

      {subsystem.dashboards.length > 0 && (
        <>
          <Heading glyph={GLYPH.dashboards} label="Dashboards" />
          <DashboardLinks dashboards={subsystem.dashboards} detailed />
        </>
      )}

      {subsystem.containers.length > 0 && (
        <>
          <Heading glyph={GLYPH.containers} label="Containers" />
          <ContainerTable containers={subsystem.containers} />
        </>
      )}

      {subsystem.probes.length > 0 && (
        <>
          <Heading glyph={GLYPH.probes} label="Probes" />
          <ProbeList probes={subsystem.probes} />
        </>
      )}

      <Heading glyph={GLYPH.units} label="Units" />
      <UnitTable units={subsystem.units} />

      <Heading glyph={GLYPH.why} label="Why this is enforced" />
      <WhyPanel id={subsystem.id} />

      {/* Only two subsystems have a writable knob, and both only tighten. */}
      {subsystem.id === "shutdown" && (
        <>
          <Heading glyph={GLYPH.stricter} label="Make it stricter" />
          <TightenCurfew />
        </>
      )}
      {subsystem.id === "hosts" && (
        <>
          <Heading glyph={GLYPH.stricter} label="Make it stricter" />
          <BlockDomain />
        </>
      )}

      {facts.length > 0 && (
        <>
          <Heading glyph={GLYPH.notes} label="Notes" />
          <dl className="facts">
            {facts.map(([key, value]) => {
              return (
                <div className="fact" key={key}>
                  <dt aria-label={key}>▸</dt>
                  <dd>{String(value)}</dd>
                </div>
              );
            })}
          </dl>
        </>
      )}

      {subsystem.logs.length > 0 && (
        <>
          <Heading glyph={GLYPH.logs} label="Logs" />
          <ul className="logs">
            {subsystem.logs.map((log) => {
              return (
                <li key={log.id}>
                  <a href={`#/logs/${log.id}`}>{log.path ?? log.unit}</a>
                  <span className="category">
                    <LogSize log={log} />
                  </span>
                </li>
              );
            })}
          </ul>
        </>
      )}
    </article>
  );
}
