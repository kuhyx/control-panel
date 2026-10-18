import { useEffect, useState } from "react";

import type {
  ContextFileDetail,
  ContextFileRow,
  ContextPanel as Data,
} from "../../lib/tokens-types.ts";

import {
  fetchContextFile,
  formatCount,
  formatUsd,
} from "../../lib/tokens-api.ts";
import { COLUMNS, OptimiseButton, shortPath } from "./context-columns.tsx";
import { DataTable } from "./data-table.tsx";
import { LineChart } from "./line-chart.tsx";
import { Markdown } from "./markdown.tsx";

function day(ts: number): string {
  const when = new Date(ts * 1000);
  return when.toISOString().slice(0, 10);
}

export function ContextPanel({
  data,
}: Readonly<{ data: Data }>): React.JSX.Element {
  const total = data.files.reduce((sum, f) => sum + f.usd_per_day, 0);
  return (
    <section className="card" id="context">
      <h2>Context files</h2>
      <DataTable<ContextFileRow>
        actions={(selected) => {
          return (
            <OptimiseButton
              measure={data.measure_command}
              rows={data.files}
              selected={selected}
            />
          );
        }}
        caption={
          <p className="category">
            Read live from disk. Standing cost = tokens (bytes / 4) ×{" "}
            {formatCount(Math.round(data.calls_per_day))} calls/day (last 7 days
            under the filters; repo files: calls in that repo) × $
            {data.price_per_mtok.toFixed(2)}/MTok cache read. Skills and agents
            count only their description. Total {formatUsd(total)}/day. Hard
            limits are Claude Code&apos;s own (content past them is not loaded);
            budgets are yours, in control_panel/tokens/context_limits.json.
          </p>
        }
        columns={COLUMNS}
        id="files"
        meta={data._tables?.files}
        rowKey={(f) => f.path}
        rows={data.files}
        title="Files"
      />
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
  if (error !== null)
    return (
      <p className="empty" role="alert">
        {error}
      </p>
    );
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
        {row === undefined ? "" : ` · ${row.status}`}
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
        {detail.git_log.map((line) => <li key={line}>{line}</li>)}
      </ul>
      <h3>content</h3>
      {detail.content === null ? (
        <p className="empty">(file is gone)</p>
      ) : (
        <div className="file-content">
          <Markdown text={detail.content} />
        </div>
      )}
    </section>
  );
}
