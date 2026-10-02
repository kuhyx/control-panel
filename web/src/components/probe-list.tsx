import type { ProbeRecord } from "../lib/types.ts";

import { ProbeDot, probeLabel } from "./probe-dot.tsx";

export function ProbeList({
  probes,
}: Readonly<{ probes: readonly ProbeRecord[] }>): React.JSX.Element {
  return (
    <ul className="dashboards">
      {probes.map((probe) => {
        return (
          <li key={`${probe.kind}:${probe.target}`}>
            <ProbeDot probe={probe} />
            <code>{probe.target}</code>
            <span className="category">
              {probe.kind} · {probeLabel(probe)}
            </span>
          </li>
        );
      })}
    </ul>
  );
}
