import type { Tables } from "../../../lib/tokens-types.ts";

import {
  formatCount,
  formatDay,
  formatShare,
  formatUsd,
} from "../../../lib/tokens-api.ts";
import { DataTable } from "../data-table.tsx";
import { LineChart } from "../line-chart.tsx";
import {
  BUDGET_COLUMNS,
  type BudgetRow,
  formatSeconds,
  HOOK_COLUMNS,
  type HookRow,
  STOP_COLUMNS,
  type StopBounceRow,
} from "./hooks-columns.tsx";

export type { BudgetRow, HookRow, StopBounceRow } from "./hooks-columns.tsx";

export interface HooksPanelData {
  _tables?: Tables;
  budget: BudgetRow[];
  budget_file: {
    caption: string;
    found: boolean;
    mtime: null | number;
    over: number;
    path: string;
  };
  caption: string;
  daily: { day: string; injected_usd: number; retry_usd: number }[];
  hooks: HookRow[];
  stop_bounces: StopBounceRow[];
  totals: {
    blocks: number;
    errors: number;
    fires: number;
    injected_usd: number;
    retry_usd: number;
    runtime_s: number;
    spend_usd: number;
    tokens: number;
    total_usd: number;
  };
}

function Tiles({
  totals,
}: Readonly<{ totals: HooksPanelData["totals"] }>): React.JSX.Element {
  const share =
    totals.spend_usd > 0 ? totals.total_usd / totals.spend_usd : null;
  const tiles: [string, string][] = [
    [formatShare(share), `of ${formatUsd(totals.spend_usd)} spend`],
    [formatCount(totals.fires), "fires"],
    [formatSeconds(totals.runtime_s), "hook runtime"],
    [formatCount(totals.tokens), "injected tokens (estimated)"],
    [formatUsd(totals.retry_usd), `retries forced by ${totals.blocks} blocks`],
    [formatCount(totals.errors), "hook errors"],
  ];
  return (
    <ul aria-label="Hook summary" className="tiles">
      <li className="tile">
        <span className="tile-count hero">{formatUsd(totals.total_usd)}</span>
        <span className="tile-label">injected context + forced retries</span>
      </li>
      {tiles.map(([value, label]) => {
        return (
          <li className="tile" key={label}>
            <span className="tile-count">{value}</span>
            <span className="tile-label">{label}</span>
          </li>
        );
      })}
    </ul>
  );
}

function Budget({
  data,
}: Readonly<{ data: HooksPanelData }>): React.JSX.Element {
  const file = data.budget_file;
  const when = file.mtime === null ? "" : ` (run ${formatDay(file.mtime)})`;
  return (
    <DataTable<BudgetRow>
      caption={
        file.found ? (
          file.caption
        ) : (
          <>
            No budget-gate result at <span className="mono">{file.path}</span>.
          </>
        )
      }
      columns={BUDGET_COLUMNS}
      id="budget"
      meta={data._tables?.budget}
      rowKey={(row, index) => `${row.event}|${row.command}|${String(index)}`}
      rows={data.budget}
      title={`Hook budget gate, last benchmark${when}: ${String(file.over)} over budget`}
    />
  );
}

export function HooksPanel({
  data,
}: Readonly<{ data: HooksPanelData }>): React.JSX.Element {
  return (
    <section className="card" id="hooks">
      <h2>Hooks (runtime, injected context, forced retries)</h2>
      <Tiles totals={data.totals} />
      <p className="caption">{data.caption}</p>
      <LineChart
        format={formatUsd}
        label="Hook cost per day"
        series={[
          {
            label: "injected context (creation + carry)",
            points: data.daily.map((d) => ({ x: d.day, y: d.injected_usd })),
          },
          {
            label: "retries forced by blocks",
            points: data.daily.map((d) => ({ x: d.day, y: d.retry_usd })),
          },
        ]}
      />
      <DataTable<HookRow>
        columns={HOOK_COLUMNS}
        id="hooks"
        meta={data._tables?.hooks}
        rowKey={(row, index) => `${row.hook}|${row.script}|${String(index)}`}
        rows={data.hooks}
        title="Per hook"
      />
      <DataTable<StopBounceRow>
        columns={STOP_COLUMNS}
        id="stop_bounces"
        meta={data._tables?.stop_bounces}
        rowKey={(row, index) => `${row.hook}|${row.script}|${String(index)}`}
        rows={data.stop_bounces}
        title="Stop-hook bounces"
      />
      <Budget data={data} />
    </section>
  );
}
