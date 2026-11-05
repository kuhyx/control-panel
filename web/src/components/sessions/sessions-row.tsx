import type { SessionEntry, SessionStatus } from "../../lib/sessions-api.ts";

import { formatRelativeAge } from "../../lib/format.ts";
import { markOf, type RowMark } from "../../lib/sessions-query.ts";
import { Markdown } from "../markdown.tsx";
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

// Select, Status, Age, Project, Title, Mark, Actions.
export const COLUMNS = 7;

const MARK_LABEL: Record<RowMark, string> = {
  manual: "by hand",
  open: "—",
  tag: "by tag",
};

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

export function SessionRows({
  isOpen,
  isSelected,
  nowMs,
  onChanged,
  onSelect,
  onToggle,
  session,
}: Readonly<{
  isOpen: boolean;
  isSelected: boolean;
  nowMs: number;
  onChanged: () => void;
  // Shift held: select the range from the last clicked row.
  onSelect: (isRange: boolean) => void;
  onToggle: () => void;
  session: SessionEntry;
}>): React.JSX.Element {
  return (
    <>
      {/* The whole row toggles; the title button is its keyboard handle (a
          click on it bubbles here); the select and actions cells stop it. */}
      <tr className={session.done ? "dim" : undefined} onClick={onToggle}>
        <td
          className="select-cell"
          onClick={(event) => {
            event.stopPropagation();
          }}
        >
          {/* onClick, not onChange: only the click carries shiftKey. */}
          <input
            aria-label={`Select ${session.id}`}
            checked={isSelected}
            onClick={(event) => {
              onSelect(event.shiftKey);
            }}
            readOnly
            type="checkbox"
          />
        </td>
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
        <td className="category">{MARK_LABEL[markOf(session)]}</td>
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
