import { GLYPH, MARK_GLYPH, SESSION_GLYPH } from "../../lib/glyphs.ts";
import { type SessionEntry, STATUS_ORDER } from "../../lib/sessions-api.ts";
import {
  AGE_UNITS,
  type AgeUnit,
  type MarkFilter,
  projectsOf,
  type SessionsQuery,
} from "../../lib/sessions-query.ts";

// Unit symbols, not words: d, h, w next to the number.
const UNIT_SPOKEN: Record<AgeUnit, string> = { d: "days", h: "hours", w: "weeks" };
// Native <option>s can only hold characters: glyphs (MARK_GLYPH), the words
// spoken via each option's aria-label.
const MARK_OPTIONS: readonly (readonly [MarkFilter, string])[] = [
  ["all", "All"],
  ["manual", "Marked done by hand"],
  ["tag", "Done by tag"],
  ["open", "Not done"],
];

// One chip per status, counted over every session, so the numbers stay put
// while other filters change: status glyph + count.
function StatusChips({
  onQuery,
  query,
  sessions,
}: Readonly<{
  onQuery: (next: SessionsQuery) => void;
  query: SessionsQuery;
  sessions: readonly SessionEntry[];
}>): React.JSX.Element {
  return (
    <fieldset aria-label="Status" className="status-chips">
      {STATUS_ORDER.map((status) => {
        const count = sessions.filter((s) => s.status === status).length;
        const isOn = query.statuses.includes(status);
        return (
          <label className="chip" key={status}>
            <input
              aria-label={`${status.replace("_", " ")} (${String(count)})`}
              checked={isOn}
              onChange={() => {
                onQuery({
                  ...query,
                  statuses: STATUS_ORDER.filter((s) =>
                    s === status ? !isOn : query.statuses.includes(s),
                  ),
                });
              }}
              type="checkbox"
            />
            <span aria-hidden="true">
              {SESSION_GLYPH[status]} {count}
            </span>
          </label>
        );
      })}
    </fieldset>
  );
}

// Every control combines with the others (AND); see filterSessions for how
// Show done relates to the status and mark filters. Each control paints a
// glyph and speaks its old label.
export function SessionsFilters({
  onQuery,
  query,
  sessions,
}: Readonly<{
  onQuery: (next: SessionsQuery) => void;
  query: SessionsQuery;
  sessions: readonly SessionEntry[];
}>): React.JSX.Element {
  const projects = projectsOf(sessions);
  if (query.project !== "" && !projects.includes(query.project)) projects.push(query.project);
  return (
    <div className="filter-bar">
      <label>
        <span aria-hidden="true">{GLYPH.search}</span>
        <input
          aria-label="Filter sessions"
          onChange={(event) => {
            onQuery({ ...query, q: event.target.value });
          }}
          type="search"
          value={query.q}
        />
      </label>
      <label>
        <span aria-hidden="true">{GLYPH.project}</span>
        <select
          aria-label="Project"
          onChange={(event) => {
            onQuery({ ...query, project: event.target.value });
          }}
          value={query.project}
        >
          <option aria-label="All projects" value="">
            {MARK_GLYPH.all}
          </option>
          {projects.map((project) => {
            return (
              <option key={project} value={project}>
                {project}
              </option>
            );
          })}
        </select>
      </label>
      <div className="age-filter">
        <label>
          <span aria-hidden="true">{GLYPH.age} &gt;</span>
          <input
            aria-label="Older than"
            min={0}
            onChange={(event) => {
              onQuery({ ...query, ageN: event.target.value });
            }}
            type="number"
            value={query.ageN}
          />
        </label>
        <select
          aria-label="Age unit"
          onChange={(event) => {
            const unit = AGE_UNITS.find((u) => u === event.target.value);
            if (unit !== undefined) onQuery({ ...query, ageUnit: unit });
          }}
          value={query.ageUnit}
        >
          {AGE_UNITS.map((unit) => {
            return (
              <option aria-label={UNIT_SPOKEN[unit]} key={unit} value={unit}>
                {unit}
              </option>
            );
          })}
        </select>
      </div>
      <label>
        <span aria-hidden="true">{GLYPH.mark}</span>
        <select
          aria-label="Mark"
          onChange={(event) => {
            const mark = MARK_OPTIONS.find(([value]) => value === event.target.value);
            if (mark !== undefined) onQuery({ ...query, mark: mark[0] });
          }}
          value={query.mark}
        >
          {MARK_OPTIONS.map(([value, label]) => {
            return (
              <option aria-label={label} key={value} value={value}>
                {MARK_GLYPH[value]}
              </option>
            );
          })}
        </select>
      </label>
      <label className="check">
        <input
          aria-label="Show done"
          checked={query.showDone}
          onChange={(event) => {
            onQuery({ ...query, showDone: event.target.checked });
          }}
          type="checkbox"
        />
        <span aria-hidden="true">{SESSION_GLYPH.done}</span>
      </label>
      <StatusChips onQuery={onQuery} query={query} sessions={sessions} />
    </div>
  );
}
