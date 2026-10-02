import type { Anomaly } from "../lib/types.ts";

import { levelTone } from "../lib/arming.ts";

export function AnomalyBanner({
  anomalies,
}: Readonly<{
  anomalies: readonly Anomaly[];
}>): React.JSX.Element {
  if (anomalies.length === 0) {
    return (
      <p className="empty" role="status">
        Nothing needs attention. Every declared unit is armed or deliberately
        retired.
      </p>
    );
  }
  return (
    // Collapsed: the findings are standing ones, and open by default they
    // buried the service table under 20+ rows on every visit.
    <details aria-label="Anomalies" className="card">
      <summary>
        <h2>{anomalies.length} finding(s)</h2>
      </summary>
      <ul className="anomaly-list">
        {anomalies.map((anomaly) => {
          return (
          <li className="anomaly" key={anomaly.id}>
            <span
              className="dot"
              style={{ backgroundColor: levelTone(anomaly.severity) }}
            />
            <div>
              <p className="anomaly-title">{anomaly.title}</p>
              <p className="anomaly-detail">{anomaly.detail}</p>
              {anomaly.evidence.length > 0 && (
                <p className="anomaly-evidence">
                  {anomaly.evidence.join(" · ")}
                </p>
              )}
            </div>
          </li>
          );
        })}
      </ul>
    </details>
  );
}
