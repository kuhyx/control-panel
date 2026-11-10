import type { Arming } from "../lib/types.ts";

import { toneFor } from "../lib/arming.ts";
import { ARMING_GLYPH } from "../lib/glyphs.ts";

const ORDER: Arming[] = [
  "ARMED",
  "UNARMED",
  "DEGRADED",
  "NOT_INSTALLED",
  "BAD",
  "UNKNOWN",
  "RETIRED",
];

export function RollupTiles({
  rollup,
}: Readonly<{
  rollup: Partial<Record<Arming, number>>;
}>): React.JSX.Element {
  const present = ORDER.filter((state) => (rollup[state] ?? 0) > 0);
  return (
    <ul aria-label="Fleet summary" className="tiles">
      {present.map((state) => {
        return (
        <li className="tile" key={state}>
          <span className="tile-count" style={{ color: toneFor(state) }}>
            {rollup[state]}
          </span>
          <span aria-label={state} className="tile-label" role="img">
            {ARMING_GLYPH[state]}
          </span>
        </li>
        );
      })}
    </ul>
  );
}
