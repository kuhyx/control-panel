import type { DashboardRecord } from "../lib/types.ts";

import { ProbeDot, probeNumbers } from "./probe-dot.tsx";

const STOPPED = "stopped (on demand)";
const STOPPED_GLYPH = "⏸";
const CLASH_GLYPH = "⚠";

// Why a dashboard is not a usable link (glyphs + spoken words), or null when
// it is. A stopped UI has nothing to open; a clashing one opens somebody
// else's server. Both render as plain text so a click can never land on the
// wrong page.
function unusable(dashboard: DashboardRecord): null | { glyphs: string; words: string } {
  const glyphs: string[] = [];
  const words: string[] = [];
  if (dashboard.stopped) {
    glyphs.push(STOPPED_GLYPH);
    words.push("stopped");
  }
  if (dashboard.clash !== null) {
    glyphs.push(CLASH_GLYPH);
    words.push("port taken");
  }
  return glyphs.length === 0 ? null : { glyphs: glyphs.join(" "), words: words.join(" · ") };
}

// Spoken name of an unusable dashboard's dot (only called for those).
function detail(dashboard: DashboardRecord): string {
  return dashboard.clash ?? STOPPED;
}

function Dot({
  dashboard,
}: Readonly<{ dashboard: DashboardRecord }>): React.JSX.Element {
  if (dashboard.clash === null && !dashboard.stopped) {
    return <ProbeDot probe={dashboard.probe} />;
  }
  return (
    <span
      aria-label={detail(dashboard)}
      className="dot probe-dot"
      role="img"
      style={{
        backgroundColor:
          dashboard.clash === null ? "var(--text-muted)" : "var(--danger)",
      }}
    />
  );
}

// Overview: one dot + label per dashboard. Detail page: also the URL and the
// probe's numbers (status, latency); the probe's sentence is spoken on the dot.
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
        const numbers = probeNumbers(dashboard.probe);
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
                  aria-label={note.words}
                  className={
                    dashboard.clash === null
                      ? "dashboard-note"
                      : "dashboard-note clash"
                  }
                  role="img"
                >
                  {note.glyphs}
                </span>
              </>
            )}
            {detailed && (
              <span className="category">
                {dashboard.url}
                {numbers !== "" && ` · ${numbers}`}
              </span>
            )}
          </li>
        );
      })}
    </ul>
  );
}
