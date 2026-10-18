import type {
  AbMetric,
  Banner,
  AbPanel as Data,
} from "../../lib/tokens-types.ts";

import { type ColumnSpec, DataTable } from "./data-table.tsx";

const COLUMNS: ColumnSpec<AbMetric>[] = [
  { key: "measure", label: "measure" },
  { key: "sonnet", label: "Sonnet", num: true },
  { key: "opus", label: "Opus", num: true },
  {
    key: "difference",
    label: "difference (Sonnet − Opus)",
    num: true,
    unit: "share, 95% CI",
  },
];

// Shown at the top of every /tokens view, not just this panel: a quality drop
// in the cheaper arm must be impossible to miss.
export function AbBanner({
  banner,
}: Readonly<{ banner: Banner }>): React.JSX.Element {
  return (
    <p className={`ab-banner ab-${banner.level}`} role="status">
      {banner.text}
    </p>
  );
}

export function AbPanel({ data }: Readonly<{ data: Data }>): React.JSX.Element {
  return (
    <section className="card" id="ab">
      <h2>A/B: judgment subagents (Sonnet vs Opus)</h2>
      {data.filtered_by === undefined ? null : (
        <p className="category">Filtered by: {data.filtered_by}</p>
      )}
      <p className="category">
        From ~/.claude/logs/agent-ab.jsonl joined to transcripts on tool_use_id.
        Rates show 95% Wilson intervals; the difference column is Sonnet − Opus
        with Newcombe&apos;s interval. {data.unjoined ?? 0} assignments not
        (yet) found in transcripts.
      </p>
      <DataTable<AbMetric>
        columns={COLUMNS}
        id="metrics"
        meta={data._tables?.metrics}
        rowKey={(row) => row.measure}
        rows={data.metrics ?? []}
        title="Measures"
      />
    </section>
  );
}
