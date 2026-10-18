import type { Tables } from "../../../lib/tokens-types.ts";

import { formatCount, formatUsd } from "../../../lib/tokens-api.ts";
import { type ColumnSpec, DataTable } from "../data-table.tsx";
import {
  countColumn,
  monoColumn,
  textColumn,
  usdColumn,
} from "./tools-columns.tsx";
import { LOOP_COLUMNS, type LoopRow } from "./tools-panel.tsx";

interface SpikeRow {
  day: string;
  median_usd: number;
  ratio: number;
  usd: number;
}

interface ExpensiveRow {
  calls: number;
  cwd: string;
  day: string;
  key: string;
  title: string;
  usd: number;
}

interface CategoryRow {
  calls: number;
  category: string;
  cost_usd: number;
  key: string;
}

type CategoryTotalRow = Omit<CategoryRow, "key">;

export interface AnomaliesPanelData {
  _tables?: Tables;
  caption: string;
  categories: CategoryRow[];
  category_totals: CategoryTotalRow[];
  expensive: ExpensiveRow[];
  loops: LoopRow[];
  over: number;
  spikes: SpikeRow[];
}

const SPIKE_COLUMNS: ColumnSpec<SpikeRow>[] = [
  textColumn<SpikeRow>("day", "day"),
  usdColumn<SpikeRow>("usd", "spend"),
  usdColumn<SpikeRow>("median_usd", "trailing 7-day median"),
  {
    format: (r) => `${r.ratio.toFixed(1)}×`,
    key: "ratio",
    label: "× median",
    num: true,
    unit: "ratio",
  },
];

const EXPENSIVE_COLUMNS: ColumnSpec<ExpensiveRow>[] = [
  monoColumn<ExpensiveRow>("key", "session"),
  textColumn<ExpensiveRow>("title", "title"),
  monoColumn<ExpensiveRow>("cwd", "cwd"),
  textColumn<ExpensiveRow>("day", "started"),
  usdColumn<ExpensiveRow>("usd", "USD"),
  countColumn<ExpensiveRow>("calls", "calls"),
];

const CATEGORY_COLUMNS: ColumnSpec<CategoryRow>[] = [
  monoColumn<CategoryRow>("key", "session"),
  textColumn<CategoryRow>("category", "category"),
  countColumn<CategoryRow>("calls", "calls"),
  usdColumn<CategoryRow>("cost_usd", "context cost"),
];

const TOTAL_COLUMNS: ColumnSpec<CategoryTotalRow>[] = [
  textColumn<CategoryTotalRow>("category", "category"),
  countColumn<CategoryTotalRow>("calls", "calls"),
  usdColumn<CategoryTotalRow>("cost_usd", "context cost"),
];

export function AnomaliesPanel({
  data,
}: Readonly<{ data: AnomaliesPanelData }>): React.JSX.Element {
  const tables = data._tables;
  return (
    <section className="card" id="anomalies">
      <h2>Anomalies</h2>
      <ul aria-label="Anomalies summary" className="tiles">
        <li className="tile">
          <span className="tile-count hero">
            {formatCount(data.spikes.length)}
          </span>
          <span className="tile-label">spend-spike days</span>
        </li>
        <li className="tile">
          <span className="tile-count">
            {formatCount(data.expensive.length)}
          </span>
          <span className="tile-label">
            sessions over {formatUsd(data.over)}
          </span>
        </li>
        <li className="tile">
          <span className="tile-count">{formatCount(data.loops.length)}</span>
          <span className="tile-label">runaway loops</span>
        </li>
      </ul>
      <p className="caption">{data.caption}</p>
      <DataTable<SpikeRow>
        columns={SPIKE_COLUMNS}
        id="spikes"
        meta={tables?.spikes}
        rowKey={(row) => row.day}
        rows={data.spikes}
        title="Day-over-day spend spikes"
      />
      <DataTable<ExpensiveRow>
        columns={EXPENSIVE_COLUMNS}
        id="expensive"
        meta={tables?.expensive}
        rowKey={(row) => row.key}
        rows={data.expensive}
        title={`Sessions over ${formatUsd(data.over)}`}
      />
      <DataTable<LoopRow>
        columns={LOOP_COLUMNS}
        id="loops"
        meta={tables?.loops}
        rowKey={(row, index) => `${row.key}|${String(index)}`}
        rows={data.loops}
        title="Runaway loops"
      />
      <DataTable<CategoryTotalRow>
        columns={TOTAL_COLUMNS}
        id="category_totals"
        meta={tables?.category_totals}
        rowKey={(row) => row.category}
        rows={data.category_totals}
        title="Polling / lint-test / VCS calls"
      />
      <DataTable<CategoryRow>
        columns={CATEGORY_COLUMNS}
        id="categories"
        meta={tables?.categories}
        rowKey={(row) => `${row.key}|${row.category}`}
        rows={data.categories}
        title="Categories per session"
      />
    </section>
  );
}
