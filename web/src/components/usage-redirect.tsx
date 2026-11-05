import { useEffect } from "react";

import { USAGE_URL } from "../lib/usage-url.ts";

// Old `#/tokens...` bookmarks: send the browser to the new home of the views.
export function UsageRedirect(): React.JSX.Element {
  useEffect(() => {
    globalThis.location.replace(USAGE_URL);
  }, []);
  return (
    <p className="empty">
      Token usage moved to <a href={USAGE_URL}>todoImplementer</a>.
    </p>
  );
}
