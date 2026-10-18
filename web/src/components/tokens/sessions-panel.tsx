import type { SessionsPanel as Data, SessionRow } from "../../lib/tokens-types.ts";

import {
  formatCount,
  formatDay,
  formatDuration,
  formatUsd,
} from "../../lib/tokens-api.ts";
import { CsvButton } from "./csv.tsx";

function shortCwd(cwd: null | string): string {
  return cwd === null ? "—" : cwd.replace(/^\/home\/[^/]+/, "~");
}

function topModel(models: Record<string, number>): string {
  const [best] = Object.entries(models).toSorted((a, b) => b[1] - a[1]);
  return best === undefined ? "—" : best[0].replace(/^claude-/, "");
}

const CSV_COLUMNS: (keyof SessionRow)[] = [
  "key",
  "cwd",
  "title",
  "first_ts",
  "active_s",
  "wall_s",
  "usd",
  "usd_sub",
  "calls",
  "prompts",
  "subagents",
  "final_tag",
];

export function SessionsPanel({ data }: Readonly<{ data: Data }>): React.JSX.Element {
  return (
    <section className="card" id="sessions">
      <h2>
        Sessions by cost{" "}
        <CsvButton
          columns={CSV_COLUMNS}
          name="sessions.csv"
          rows={data.sessions}
        />
      </h2>
      <p className="category">
        Top {data.limit} sessions that started in range. Active time sums the gaps
        between consecutive records of the session and its subagents, a gap over 5
        minutes counting as zero; wall time is first to last record.
      </p>
      <div className="table-scroll">
        <table className="table tokens-table">
          <thead>
            <tr>
              <th>started</th>
              <th>repo / cwd</th>
              <th>first prompt</th>
              <th className="num">active</th>
              <th className="num">wall</th>
              <th className="num">USD</th>
              <th className="num">of which agents</th>
              <th className="num">calls</th>
              <th className="num">prompts</th>
              <th>model</th>
              <th>end</th>
            </tr>
          </thead>
          <tbody>
            {data.sessions.map((s) => {
              return (
                <tr key={s.key}>
                  <td>{formatDay(s.first_ts)}</td>
                  <td className="mono">{shortCwd(s.cwd)}</td>
                  <td>
                    <a href={`#/tokens/s/${encodeURIComponent(s.key)}`}>
                      {s.title === "" ? s.key : s.title}
                    </a>
                  </td>
                  <td className="num strong">{formatDuration(s.active_s)}</td>
                  <td className="num">{formatDuration(s.wall_s)}</td>
                  <td className="num strong">{formatUsd(s.usd)}</td>
                  <td className="num">{formatUsd(s.usd_sub)}</td>
                  <td className="num">{formatCount(s.calls)}</td>
                  <td className="num">{s.prompts}</td>
                  <td>{topModel(s.models)}</td>
                  <td>{s.final_tag ?? "—"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
