import type { DashboardRecord } from "../lib/types.ts";

import { ProbeDot, probeLabel } from "./probe-dot.tsx";

// Every dashboard opens in its own tab: the panel is the hub you come back to,
// and losing it to a navigation would mean re-finding it from the tray.
export function DashboardLinks({
  dashboards,
  detailed = false,
}: Readonly<{
  dashboards: readonly DashboardRecord[];
  detailed?: boolean;
}>): null | React.JSX.Element {
  if (dashboards.length === 0) return null;
  return (
    <ul className="dashboards">
      {dashboards.map((dashboard) => {
        return (
          <li key={dashboard.url}>
            <ProbeDot probe={dashboard.probe} />
            <a href={dashboard.url} rel="noopener noreferrer" target="_blank">
              {dashboard.label}
            </a>
            {detailed && (
              <span className="category">
                {dashboard.url} · {probeLabel(dashboard.probe)}
              </span>
            )}
          </li>
        );
      })}
    </ul>
  );
}
