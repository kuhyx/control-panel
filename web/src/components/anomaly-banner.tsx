import type { Anomaly } from "../lib/types.ts";

import { levelTone } from "../lib/arming.ts";
import { GLYPH } from "../lib/glyphs.ts";

// Each finding is a server-built sentence ("x.timer is NOT_INSTALLED"): the
// row paints a severity dot and a link to the subsystem it is about; the
// title and detail are its spoken name.
export function AnomalyBanner({
  anomalies,
}: Readonly<{
  anomalies: readonly Anomaly[];
}>): React.JSX.Element {
  if (anomalies.length === 0) {
    // Every declared unit is armed or deliberately retired.
    return (
      <p aria-label="Nothing needs attention" className="empty" role="status">
        {GLYPH.ok}
      </p>
    );
  }
  return (
    // Collapsed: the findings are standing ones, and open by default they
    // buried the service table under 20+ rows on every visit.
    <details aria-label="Anomalies" className="card">
      <summary>
        <h2 aria-label="Findings">
          {anomalies.length} {GLYPH.findings}
        </h2>
      </summary>
      <ul className="anomaly-list">
        {anomalies.map((anomaly) => {
          return (
            <li
              aria-label={`${anomaly.title}: ${anomaly.detail}`}
              className="anomaly"
              key={anomaly.id}
            >
              <span
                className="dot"
                style={{ backgroundColor: levelTone(anomaly.severity) }}
              />
              <a href={`#/s/${anomaly.subsystem}`}>
                <code>{anomaly.subsystem}</code>
              </a>
            </li>
          );
        })}
      </ul>
    </details>
  );
}
