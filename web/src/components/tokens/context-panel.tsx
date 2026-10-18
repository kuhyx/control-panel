import { useEffect, useState } from "react";

import type {
  ContextFileDetail,
  ContextPanel as Data,
} from "../../lib/tokens-types.ts";

import { fetchContextFile, formatCount, formatUsd } from "../../lib/tokens-api.ts";
import { CsvButton } from "./csv.tsx";
import { LineChart } from "./line-chart.tsx";

function shortPath(path: string): string {
  return path.replace(/^\/home\/[^/]+/, "~");
}

function day(ts: number): string {
  const when = new Date(ts * 1000);
  return when.toISOString().slice(0, 10);
}

export function ContextPanel({ data }: Readonly<{ data: Data }>): React.JSX.Element {
  const total = data.files.reduce((sum, f) => sum + f.usd_per_day, 0);
  return (
    <section className="card" id="context">
      <h2>
        Context files{" "}
        <CsvButton
          columns={["path", "kind", "standing", "bytes", "tokens", "usd_per_day", "warning"]}
          name="context-files.csv"
          rows={data.files}
        />
      </h2>
      <p className="category">
        Read live from disk. Standing cost = tokens (bytes / 4) ×{" "}
        {formatCount(Math.round(data.calls_per_day))} calls/day (last 7 days; repo
        files: calls in that repo) × ${data.price_per_mtok.toFixed(2)}/MTok cache read.
        Skills and agents count only their description. Total {formatUsd(total)}/day.
      </p>
      <div className="table-scroll">
        <table className="table tokens-table">
          <thead>
            <tr>
              <th>file</th>
              <th>kind</th>
              <th className="num">bytes</th>
              <th className="num">tokens loaded</th>
              <th className="num">$/day</th>
              <th>limit</th>
              <th className="num">history</th>
            </tr>
          </thead>
          <tbody>
            {data.files.map((f) => {
              return (
                <tr key={f.path}>
                  <td className="mono">
                    <a href={`#/tokens/f/${encodeURIComponent(f.path)}`}>
                      {shortPath(f.path)}
                    </a>
                  </td>
                  <td>{f.kind}</td>
                  <td className="num">{f.bytes === null ? "gone" : formatCount(f.bytes)}</td>
                  <td className="num">{formatCount(f.tokens)}</td>
                  <td className="num strong">{formatUsd(f.usd_per_day)}</td>
                  <td>{f.warning === null ? "" : <span className="badge warn-badge">{f.warning}</span>}</td>
                  <td className="num">{f.history.length} points</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export function ContextFile({
  data,
  path,
}: Readonly<{ data: Data | null; path: string }>): React.JSX.Element {
  const [detail, setDetail] = useState<ContextFileDetail | null>(null);
  const [error, setError] = useState<null | string>(null);
  useEffect(() => {
    const controller = new AbortController();
    const load = async (): Promise<void> => {
      try {
        setDetail(await fetchContextFile(path, controller.signal));
      } catch (error_: unknown) {
        if (!controller.signal.aborted) setError(String(error_));
      }
    };
    void load();
    return () => {
      controller.abort();
    };
  }, [path]);
  if (error !== null) return <p className="empty" role="alert">{error}</p>;
  if (detail === null) return <p className="empty">Reading…</p>;
  const row = data?.files.find((f) => f.path === path);
  return (
    <section className="card">
      <p>
        <a href="#/tokens">← tokens</a>
      </p>
      <h2 className="mono">{shortPath(detail.path)}</h2>
      <p className="category">
        {detail.kind}
        {row === undefined
          ? ""
          : ` · ${formatCount(row.tokens)} tokens loaded · ${formatUsd(row.usd_per_day)}/day`}
        {row?.warning == null ? "" : ` · ${row.warning}`}
      </p>
      {row !== undefined && row.history.length > 0 && (
        <LineChart
          format={(n) => formatCount(Math.round(n))}
          label={`size of ${detail.path} over time`}
          series={[
            {
              label: "bytes",
              points: row.history.map((h) => ({ x: day(h.ts), y: h.bytes })),
            },
          ]}
        />
      )}
      <h3>git log (read-only)</h3>
      <ul className="git-log mono">
        {detail.git_log.length === 0 ? <li>not tracked by git</li> : null}
        {detail.git_log.map((line) => {
          return (
            <li key={line}>{line}</li>
          );
        })}
      </ul>
      <h3>content</h3>
      <pre className="file-content">{detail.content ?? "(file is gone)"}</pre>
    </section>
  );
}
