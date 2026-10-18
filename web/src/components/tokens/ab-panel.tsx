import type {
  AbArm,
  Banner,
  AbPanel as Data,
  RateCi,
} from "../../lib/tokens-types.ts";

import { formatDuration, formatShare, formatUsd } from "../../lib/tokens-api.ts";

const RATES: { key: "correction" | "error" | "followup" | "redo"; label: string }[] =
  [
    { key: "redo", label: "redo rate (similar Agent re-dispatched)" },
    { key: "followup", label: "follow-up rate (SendMessage after return)" },
    { key: "error", label: "error / aborted rate" },
    { key: "correction", label: "user-correction rate (noisy: phrase match)" },
  ];

const ARMS = ["sonnet", "opus"] as const;

function rate(ci: RateCi | undefined): string {
  return ci?.rate == null ? "—" : `${formatShare(ci.rate)} [${formatShare(ci.low)}, ${formatShare(ci.high)}]`;
}

// Shown at the top of every /tokens view, not just this panel: a quality drop
// in the cheaper arm must be impossible to miss.
export function AbBanner({ banner }: Readonly<{ banner: Banner }>): React.JSX.Element {
  return (
    <p className={`ab-banner ab-${banner.level}`} role="status">
      {banner.text}
    </p>
  );
}

function armCell(arm: AbArm | undefined, render: (a: AbArm) => string): string {
  return arm === undefined ? "—" : render(arm);
}

export function AbPanel({ data }: Readonly<{ data: Data }>): React.JSX.Element {
  const { arms, diffs } = data;
  return (
    <section className="card" id="ab">
      <h2>A/B: judgment subagents (Sonnet vs Opus)</h2>
      {data.filtered_by === undefined ? null : (
        <p className="category">Filtered by: {data.filtered_by}</p>
      )}
      <p className="category">
        From ~/.claude/logs/agent-ab.jsonl joined to transcripts on tool_use_id.
        Rates show 95% Wilson intervals; the difference column is Sonnet − Opus with
        Newcombe&apos;s interval. {data.unjoined ?? 0} assignments not (yet) found in
        transcripts.
      </p>
      <table className="table tokens-table">
        <thead>
          <tr>
            <th>measure</th>
            <th className="num">Sonnet</th>
            <th className="num">Opus</th>
            <th className="num">difference</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>n</td>
            {ARMS.map((name) => {
              return (
                <td className="num" key={name}>
                  {arms[name]?.n ?? 0}
                </td>
              );
            })}
            <td />
          </tr>
          <tr>
            <td>cost per agent (mean, 95% CI)</td>
            {ARMS.map((name) => {
              return (
                <td className="num" key={name}>
                  {armCell(arms[name], (a) => `${formatUsd(a.usd.mean)} [${formatUsd(a.usd.low)}, ${formatUsd(a.usd.high)}]`)}
                </td>
              );
            })}
            <td />
          </tr>
          <tr>
            <td>duration (mean)</td>
            {ARMS.map((name) => {
              return (
                <td className="num" key={name}>
                  {armCell(arms[name], (a) => formatDuration(a.duration_s.mean))}
                </td>
              );
            })}
            <td />
          </tr>
          {RATES.map((r) => {
            const diff = diffs?.[r.key];
            return (
              <tr key={r.key}>
                <td>{r.label}</td>
                {ARMS.map((name) => {
                  return (
                    <td className="num" key={name}>
                      {rate(arms[name]?.[r.key])}
                    </td>
                  );
                })}
                <td className="num">
                  {diff === undefined
                    ? "—"
                    : `${formatShare(diff.diff)} [${formatShare(diff.low)}, ${formatShare(diff.high)}]`}
                </td>
              </tr>
            );
          })}
          <tr>
            <td>parent session end tag</td>
            {ARMS.map((name) => {
              return (
                <td className="num" key={name}>
                  {armCell(arms[name], (a) => {
                    return Object.entries(a.tags)
                      .map(([tag, n]) => `${tag} ${String(n)}`)
                      .join(", ");
                  },
                  )}
                </td>
              );
            })}
            <td />
          </tr>
        </tbody>
      </table>
    </section>
  );
}
