import { useEffect, useState } from "react";

import type {
  SessionDetail as Detail,
  PromptRow,
  SubagentRow,
} from "../../lib/tokens-types.ts";

import {
  fetchSession,
  formatCount,
  formatDay,
  formatDuration,
  formatShare,
  formatUsd,
} from "../../lib/tokens-api.ts";

function Subagents({ rows }: Readonly<{ rows: SubagentRow[] }>): React.JSX.Element {
  return (
    <table className="table tokens-table">
      <thead>
        <tr>
          <th>subagent</th>
          <th>type</th>
          <th>model</th>
          <th className="num">USD</th>
          <th className="num">wall</th>
          <th className="num">active</th>
          <th className="num">calls</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((a) => {
          return (
            <tr key={a.key}>
              <td>
                {a.depth > 1 ? "↳ ".repeat(a.depth - 1) : ""}
                {a.description}
              </td>
              <td>{a.agent_type}</td>
              <td>{a.model.replace(/^claude-/, "")}</td>
              <td className="num strong">{formatUsd(a.usd)}</td>
              <td className="num">{formatDuration(a.wall_s)}</td>
              <td className="num">{formatDuration(a.active_s)}</td>
              <td className="num">{formatCount(a.calls)}</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

function Prompt({ prompt }: Readonly<{ prompt: PromptRow }>): React.JSX.Element {
  return (
    <li className="prompt">
      <div className="prompt-head">
        <span className="prompt-cost">{formatUsd(prompt.usd)}</span>
        <span className="prompt-text">{prompt.text}</span>
        <span className="category">
          {formatDay(prompt.ts)} · active {formatDuration(prompt.active_s)} · own{" "}
          {formatUsd(prompt.usd_own)} + agents {formatUsd(prompt.usd_sub)} ·{" "}
          {prompt.calls} calls
        </span>
      </div>
      {prompt.subagents.length > 0 && <Subagents rows={prompt.subagents} />}
      {prompt.tools.length > 0 && (
        <table className="table tokens-table">
          <thead>
            <tr>
              <th>tool</th>
              <th className="num">calls</th>
              <th className="num">result tokens</th>
              <th className="num">USD (issuing calls)</th>
              <th className="num">share of prompt</th>
              <th className="num">carry USD</th>
            </tr>
          </thead>
          <tbody>
            {prompt.tools.map((t) => {
              return (
                <tr key={t.name}>
                  <td className="mono">{t.name}</td>
                  <td className="num">{formatCount(t.calls)}</td>
                  <td className="num">{formatCount(t.result_tokens)}</td>
                  <td className="num">{formatUsd(t.usd)}</td>
                  <td className="num">{formatShare(t.share)}</td>
                  <td className="num">{formatUsd(t.carry_usd)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </li>
  );
}

export function SessionDetail({ id }: Readonly<{ id: string }>): React.JSX.Element {
  const [detail, setDetail] = useState<Detail | null>(null);
  const [error, setError] = useState<null | string>(null);
  useEffect(() => {
    const controller = new AbortController();
    const load = async (): Promise<void> => {
      try {
        setDetail(await fetchSession(id, controller.signal));
      } catch (error_: unknown) {
        if (!controller.signal.aborted) setError(String(error_));
      }
    };
    void load();
    return () => {
      controller.abort();
    };
  }, [id]);
  if (error !== null) return <p className="empty" role="alert">{error}</p>;
  if (detail === null) return <p className="empty">Reading…</p>;
  const { session } = detail;
  return (
    <section className="card">
      <p>
        <a href="#/tokens">← all sessions</a>
      </p>
      <h2>{session.title === "" ? session.key : session.title}</h2>
      <p className="category">
        {session.cwd} · {formatDay(session.first_ts)} · <strong>active{" "}
        {formatDuration(session.active_s)}</strong> of {formatDuration(session.wall_s)} wall ·{" "}
        {formatUsd(session.usd)} ({formatUsd(session.usd_sub)} in {session.subagents}{" "}
        subagents) · {formatCount(session.calls)} calls · ended{" "}
        {session.final_tag ?? "untagged"}
      </p>
      <p className="category">
        Prompts sorted by cost. A turn&apos;s USD is split evenly across the tools it
        called (&quot;(no tool)&quot; for text-only turns); carry USD is what the
        result cost by being re-read on every later call until a compaction.
      </p>
      <ol className="prompts">
        {detail.prompts.map((p) => {
          return (
            <Prompt key={p.idx} prompt={p} />
          );
        })}
      </ol>
      {detail.unattributed.length > 0 && (
        <>
          <h3>Unattributed subagents (spawn not found, e.g. outlived /clear)</h3>
          <Subagents rows={detail.unattributed} />
        </>
      )}
    </section>
  );
}
