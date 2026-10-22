import { useState } from "react";

import type { SessionEntry, SessionStatus } from "../../lib/sessions-api.ts";

import { formatRelativeAge } from "../../lib/format.ts";
import { Markdown } from "../tokens/markdown.tsx";
import { SessionActions } from "./session-actions.tsx";

// Semantic fills only, as StateBadge does: what wants kuhy (a pending action
// or question) is the danger tone, an unknown state the warning one, live
// work info, and anything finished is muted.
const TONE: Record<SessionStatus, string> = {
  continuing: "var(--text-muted)",
  done: "var(--text-muted)",
  needs_action: "var(--danger)",
  question: "var(--danger)",
  running: "var(--info)",
  untagged: "var(--warning)",
};

const COLUMNS = 5;

function StatusBadge({
  status,
}: Readonly<{ status: SessionStatus }>): React.JSX.Element {
  return (
    <span className="badge" style={{ backgroundColor: TONE[status] }}>
      {status.replace("_", " ")}
    </span>
  );
}

function SessionDetail({
  session,
}: Readonly<{ session: SessionEntry }>): React.JSX.Element {
  return (
    <>
      <dl className="session-meta">
        <dt>cwd</dt>
        <dd>
          <code>{session.cwd}</code>
        </dd>
        <dt>session</dt>
        <dd>
          <code>{session.id}</code>
        </dd>
      </dl>
      <h4>Last prompt</h4>
      <p className="session-text">{session.last_user}</p>
      <h4>Last reply</h4>
      <Markdown text={session.last_assistant} />
    </>
  );
}

function SessionRows({
  isOpen,
  nowMs,
  onChanged,
  onToggle,
  session,
}: Readonly<{
  isOpen: boolean;
  nowMs: number;
  onChanged: () => void;
  onToggle: () => void;
  session: SessionEntry;
}>): React.JSX.Element {
  return (
    <>
      {/* The whole row toggles; the title button is its keyboard handle (a
          click on it bubbles here), and the actions cell stops the bubble. */}
      <tr className={session.done ? "dim" : undefined} onClick={onToggle}>
        <td>
          <StatusBadge status={session.status} />
        </td>
        <td className="num" title={session.last_ts}>
          {formatRelativeAge(session.last_ts, nowMs)}
        </td>
        <td>{session.project}</td>
        <td>
          <button aria-expanded={isOpen} className="link-button" type="button">
            {session.title === "" ? "(untitled)" : session.title}
          </button>
        </td>
        <td
          onClick={(event) => {
            event.stopPropagation();
          }}
        >
          <SessionActions onChanged={onChanged} session={session} />
        </td>
      </tr>
      {isOpen && (
        <tr className="session-detail">
          <td colSpan={COLUMNS}>
            <SessionDetail session={session} />
          </td>
        </tr>
      )}
    </>
  );
}

// Rows keyed by session id, and the open set held here (the table stays
// mounted across refetches), so a refresh keeps expanded rows and each row's
// last action result.
export function SessionsTable({
  nowMs,
  onChanged,
  sessions,
}: Readonly<{
  nowMs: number;
  onChanged: () => void;
  sessions: readonly SessionEntry[];
}>): React.JSX.Element {
  const [open, setOpen] = useState<ReadonlySet<string>>(new Set());
  const toggle = (id: string): void => {
    const next = new Set(open);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setOpen(next);
  };
  return (
    <div className="table-scroll">
      <table className="table tokens-table sessions-table">
        <thead>
          <tr>
            <th>Status</th>
            <th>Age</th>
            <th>Project</th>
            <th>Title</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {sessions.map((session) => {
            return (
              <SessionRows
                isOpen={open.has(session.id)}
                key={session.id}
                nowMs={nowMs}
                onChanged={onChanged}
                onToggle={() => {
                  toggle(session.id);
                }}
                session={session}
              />
            );
          })}
          {sessions.length === 0 && (
            <tr>
              <td className="empty" colSpan={COLUMNS}>
                No sessions match.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
