import { useEffect } from "react";

import { GLYPH } from "../lib/glyphs.ts";
import { USAGE_URL } from "../lib/usage-url.ts";

// Token usage moved to todoImplementer; an old bookmark lands here and is sent
// on, with a link in case the redirect is blocked.
export function UsageRedirect(): React.JSX.Element {
  useEffect(() => {
    globalThis.location.replace(USAGE_URL);
  }, []);
  return (
    <p aria-label="Token usage moved" className="empty" role="status">
      {GLYPH.reading}{" "}
      <a aria-label="todoImplementer" href={USAGE_URL}>
        <span aria-hidden="true">{GLYPH.usage}</span>
      </a>
    </p>
  );
}
