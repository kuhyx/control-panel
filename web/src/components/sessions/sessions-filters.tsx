import { type SessionEntry, STATUS_ORDER } from "../../lib/sessions-api.ts";
import {
  AGE_UNITS,
  type AgeUnit,
  type MarkFilter,
  projectsOf,
  type SessionsQuery,
} from "../../lib/sessions-query.ts";

const UNIT_LABEL: Record<AgeUnit, string> = { d: "days", h: "hours", w: "weeks" };
const MARK_OPTIONS: readonly (readonly [MarkFilter, string])[] = [
  ["all", "All"],
  ["manual", "Marked done by hand"],
  ["tag", "Done by tag"],
  ["open", "Not done"],
];

// One chip per status, counted over every session (like the header line), so
// the numbers stay put while other filters change.
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
    <fieldset className="status-chips">
      <legend>Status</legend>
      {STATUS_ORDER.map((status) => {
        const count = sessions.filter((s) => s.status === status).length;
        const isOn = query.statuses.includes(status);
        return (
          <label className="chip" key={status}>
            <input
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
            {status.replace("_", " ")} ({count})
          </label>
        );
      })}
    </fieldset>
  );
}

// Every control combines with the others (AND); see filterSessions for how
// Show done relates to the status and mark filters.
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
        Filter sessions
        <input
          onChange={(event) => {
            onQuery({ ...query, q: event.target.value });
          }}
          placeholder="project, title or cwd"
          type="search"
          value={query.q}
        />
      </label>
      <label>
        Project
        <select
          onChange={(event) => {
            onQuery({ ...query, project: event.target.value });
          }}
          value={query.project}
        >
          <option value="">All projects</option>
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
          Older than
          <input
            min={0}
            onChange={(event) => {
              onQuery({ ...query, ageN: event.target.value });
            }}
            placeholder="off"
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
              <option key={unit} value={unit}>
                {UNIT_LABEL[unit]}
              </option>
            );
          })}
        </select>
      </div>
      <label>
        Mark
        <select
          onChange={(event) => {
            const mark = MARK_OPTIONS.find(([value]) => value === event.target.value);
            if (mark !== undefined) onQuery({ ...query, mark: mark[0] });
          }}
          value={query.mark}
        >
          {MARK_OPTIONS.map(([value, label]) => {
            return (
              <option key={value} value={value}>
                {label}
              </option>
            );
          })}
        </select>
      </label>
      <label className="check">
        <input
          checked={query.showDone}
          onChange={(event) => {
            onQuery({ ...query, showDone: event.target.checked });
          }}
          type="checkbox"
        />
        Show done
      </label>
      <StatusChips onQuery={onQuery} query={query} sessions={sessions} />
    </div>
  );
}
