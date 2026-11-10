import type { ProbeRecord } from "../lib/types.ts";

import { Glyph } from "./glyph.tsx";
import { ProbeDot, probeNumbers } from "./probe-dot.tsx";

// Probe kinds the collector emits (control_panel/_probe.py).
const KIND_GLYPH: Readonly<Record<string, string>> = { file: "📄", http: "🌐", tcp: "🔌" };

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
              <Glyph glyph={KIND_GLYPH[probe.kind] ?? "•"} label={probe.kind} />{" "}
              {probeNumbers(probe)}
            </span>
          </li>
        );
      })}
    </ul>
  );
}
