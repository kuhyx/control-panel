import type { Arming } from "../lib/types.ts";

import { toneFor } from "../lib/arming.ts";
import { ARMING_GLYPH } from "../lib/glyphs.ts";

// web-ui ships no Badge. This follows the Card entry in
// ~/src/utils/unified-design-system/components.html, which specifies that status
// cells use a semantic fill with --on-fill text — never a categorical hue.
// The fill is one channel, the glyph's shape the other; the state word is
// spoken only.
export function StateBadge({
  state,
}: Readonly<{ state: Arming }>): React.JSX.Element {
  return (
    <span
      aria-label={state}
      className="badge"
      role="img"
      style={{ backgroundColor: toneFor(state) }}
    >
      {ARMING_GLYPH[state]}
    </span>
  );
}
