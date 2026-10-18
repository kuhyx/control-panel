import type { TokenQuery } from "../../lib/tokens-api.ts";
import type { TokensIndex } from "../../lib/tokens-types.ts";

// One row of filters above every panel: date range (or an exact token_audit
// snapshot window), repo/cwd, model, and main-vs-subagent scope.
export function FilterBar({
  index,
  onChange,
  query,
}: Readonly<{
  index: TokensIndex;
  onChange: (next: TokenQuery) => void;
  query: TokenQuery;
}>): React.JSX.Element {
  const set = (key: keyof TokenQuery, value: string): void => {
    onChange({ ...query, [key]: value });
  };
  return (
    <form
      aria-label="Token filters"
      className="filter-bar"
      onSubmit={(event) => {
        event.preventDefault();
      }}
    >
      <label>
        from
        <input
          onChange={(event) => {
            set("from", event.target.value);
          }}
          type="date"
          value={query.from}
        />
      </label>
      <label>
        to
        <input
          onChange={(event) => {
            set("to", event.target.value);
          }}
          type="date"
          value={query.to}
        />
      </label>
      <label>
        snapshot window
        <select
          onChange={(event) => {
            set("window", event.target.value);
          }}
          value={query.window}
        >
          <option value="">—</option>
          {index.coverage.snapshots.map((name) => {
            return (
              <option key={name} value={name}>
                {name}
              </option>
            );
          })}
        </select>
      </label>
      <label>
        repo / cwd
        <select
          onChange={(event) => {
            set("cwd", event.target.value);
          }}
          value={query.cwd}
        >
          <option value="">all</option>
          {index.options.cwds.map((cwd) => {
            return (
              <option key={cwd} value={cwd}>
                {cwd.replace(/^\/home\/[^/]+/, "~")}
              </option>
            );
          })}
        </select>
      </label>
      <label>
        model
        <select
          onChange={(event) => {
            set("model", event.target.value);
          }}
          value={query.model}
        >
          <option value="">all</option>
          {index.options.models.map((model) => {
            return (
              <option key={model} value={model}>
                {model}
              </option>
            );
          })}
        </select>
      </label>
      <label>
        scope
        <select
          onChange={(event) => {
            set("scope", event.target.value);
          }}
          value={query.scope}
        >
          <option value="all">main + subagents</option>
          <option value="main">main only</option>
          <option value="sub">subagents only</option>
        </select>
      </label>
    </form>
  );
}
