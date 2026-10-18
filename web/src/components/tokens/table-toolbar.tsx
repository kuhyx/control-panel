import { useState } from "react";

import { DraftInput } from "./draft-input.tsx";

export interface Counts {
  matched: number;
  shown: number;
  total: number;
}

// Build the text (which may fetch every matching row) and copy it.
async function didCopy(build: () => Promise<string>): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(await build());
    return true;
  } catch {
    return false;
  }
}

// Search box, row counts and the export actions of one table.
export function TableToolbar({
  counts,
  csvHref,
  csvName,
  forClaude,
  json,
  onSearch,
  onShowAll,
  search,
  selected,
}: Readonly<{
  counts: Counts;
  csvHref: string;
  csvName: string;
  forClaude: () => Promise<string>;
  json: () => Promise<string>;
  onSearch: (q: string) => void;
  onShowAll: () => void;
  search: string;
  selected: number;
}>): React.JSX.Element {
  const [status, setStatus] = useState("");
  const run = (label: string, build: () => Promise<string>): void => {
    void didCopy(build).then((ok) => {
      setStatus(ok ? `${label}: copied` : `${label}: copy failed`);
    });
  };
  const which =
    selected > 0 ? `${String(selected)} selected` : "every matching row";
  return (
    <div className="table-toolbar">
      <DraftInput
        label="search this table"
        onCommit={onSearch}
        placeholder="search"
        value={search}
      />
      <span className="category">
        {counts.shown} shown of {counts.matched} matching ({counts.total} total)
      </span>
      {counts.shown < counts.matched && (
        <button className="table-button" onClick={onShowAll} type="button">
          Show all
        </button>
      )}
      <button
        className="table-button"
        onClick={() => {
          run("Copy for Claude", forClaude);
        }}
        title={`markdown table of ${which}`}
        type="button"
      >
        Copy for Claude
      </button>
      <button
        className="table-button"
        onClick={() => {
          run("Copy as JSON", json);
        }}
        title={`JSON of ${which}`}
        type="button"
      >
        Copy as JSON
      </button>
      <a className="csv-link" download={csvName} href={csvHref}>
        CSV
      </a>
      <span aria-live="polite" className="category">
        {status}
      </span>
    </div>
  );
}
