import type { Arming } from "../lib/types.ts";

import { toneFor } from "../lib/arming.ts";

// web-ui ships no Badge. This follows the Card entry in
// ~/utils/unified-design-system/components.html, which specifies that status
// cells use a semantic fill with --on-fill text — never a categorical hue.
export function StateBadge({
  state,
}: Readonly<{ state: Arming }>): React.JSX.Element {
  return (
    <span
      className="badge"
      style={{ backgroundColor: toneFor(state) }}
      title={state}
    >
      {state}
    </span>
  );
}
