import type { DashboardRecord } from "../lib/types.ts";

import { ProbeDot, probeLabel } from "./probe-dot.tsx";

const STOPPED = "stopped (on demand)";

// Why a dashboard is not a usable link, or null when it is. A stopped UI has
// nothing to open; a clashing one opens somebody else's server. Both render as
// plain text so a click can never land on the wrong page.
function unusable(dashboard: DashboardRecord): null | string {
  const notes: string[] = [];
  if (dashboard.stopped) notes.push("stopped");
  if (dashboard.clash !== null) notes.push("port taken");
  return notes.length === 0 ? null : notes.join(" · ");
}

function detail(dashboard: DashboardRecord): string {
  if (dashboard.clash !== null) return dashboard.clash;
  return dashboard.stopped ? STOPPED : probeLabel(dashboard.probe);
}

function Dot({
  dashboard,
}: Readonly<{ dashboard: DashboardRecord }>): React.JSX.Element {
  if (dashboard.clash === null && !dashboard.stopped) {
    return <ProbeDot probe={dashboard.probe} />;
  }
  const label = detail(dashboard);
  return (
    <span
      aria-label={label}
      className="dot probe-dot"
      role="img"
      style={{
        backgroundColor:
          dashboard.clash === null ? "var(--text-muted)" : "var(--danger)",
      }}
      title={label}
    />
  );
}

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
        const note = unusable(dashboard);
        return (
          <li key={dashboard.url}>
            <Dot dashboard={dashboard} />
            {note === null ? (
              <a href={dashboard.url} rel="noopener noreferrer" target="_blank">
                {dashboard.label}
              </a>
            ) : (
              <>
                <span>{dashboard.label}</span>
                <span
                  className={
                    dashboard.clash === null
                      ? "dashboard-note"
                      : "dashboard-note clash"
                  }
                  title={detail(dashboard)}
                >
                  {note}
                </span>
              </>
            )}
            {detailed && (
              <span className="category">
                {dashboard.url} · {detail(dashboard)}
              </span>
            )}
          </li>
        );
      })}
    </ul>
  );
}
