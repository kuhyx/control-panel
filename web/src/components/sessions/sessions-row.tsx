import type { SessionEntry, SessionStatus } from "../../lib/sessions-api.ts";

import { formatRelativeAge } from "../../lib/format.ts";
import { MARK_GLYPH, SESSION_GLYPH } from "../../lib/glyphs.ts";
import { markOf, type RowMark } from "../../lib/sessions-query.ts";
import { Glyph } from "../glyph.tsx";
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

// Same glyphs as the Mark filter; an open row is a plain dash.
const MARK_SPOKEN: Record<RowMark, string> = {
  manual: "by hand",
  open: "not done",
  tag: "by tag",
};

function MarkCell({ mark }: Readonly<{ mark: RowMark }>): React.JSX.Element {
  return <Glyph glyph={mark === "open" ? "—" : MARK_GLYPH[mark]} label={MARK_SPOKEN[mark]} />;
}

// Tone fill plus the status glyph; the status word is spoken.
function StatusBadge({
  status,
}: Readonly<{ status: SessionStatus }>): React.JSX.Element {
  return (
    <span
      aria-label={status.replace("_", " ")}
      className="badge"
      role="img"
      style={{ backgroundColor: TONE[status] }}
    >
      {SESSION_GLYPH[status]}
    </span>
  );
}

function SessionDetail({
  session,
}: Readonly<{ session: SessionEntry }>): React.JSX.Element {
  return (
    <>
      <dl className="session-meta">
        <dt aria-label="cwd">·</dt>
        <dd>
          <code>{session.cwd}</code>
        </dd>
        <dt aria-label="session">◎</dt>
        <dd>
          <code>{session.id}</code>
        </dd>
      </dl>
      <span aria-label="Last prompt">▲</span>
      <p className="session-text">{session.last_user}</p>
      <span aria-label="Last reply">▼</span>
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
            {session.title === "" ? <Glyph glyph="—" label="(untitled)" /> : session.title}
          </button>
        </td>
        <td className="category">
          <MarkCell mark={markOf(session)} />
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
