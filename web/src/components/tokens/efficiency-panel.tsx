import type {
  EfficiencyPanel as Data,
  EfficiencyWeek,
} from "../../lib/tokens-types.ts";

import { formatShare, formatUsd } from "../../lib/tokens-api.ts";
import { DataTable } from "./data-table.tsx";
import { LineChart } from "./line-chart.tsx";

const TABLES = [
  { id: "done", title: "DONE sessions per week" },
  { id: "commits", title: "Surviving commits per week" },
  { id: "estimate", title: "Estimated size units per week" },
] as const;

function WeeklyTable({
  data,
  table,
}: Readonly<{
  data: Data;
  table: (typeof TABLES)[number];
}>): React.JSX.Element {
  const rows = data[table.id];
  const keys = [...new Set(rows.flatMap((row) => Object.keys(row)))];
  return (
    <DataTable<EfficiencyWeek>
      columns={keys.map((key) => ({ key, label: key, num: key !== "week" }))}
      id={table.id}
      meta={data._tables?.[table.id]}
      rowKey={(row) => row.week}
      rows={rows}
      title={table.title}
    />
  );
}

function points(
  rows: EfficiencyWeek[],
  key: string,
): { x: string; y: null | number }[] {
  return rows.map((row) => {
    const value = row[key];
    return { x: row.week, y: typeof value === "number" ? value : null };
  });
}

function total(rows: EfficiencyWeek[], key: string): number {
  let sum = 0;
  for (const row of rows) {
    const value = row[key];
    if (typeof value === "number") sum += value;
  }
  return sum;
}

export function EfficiencyPanel({
  data,
}: Readonly<{ data: Data }>): React.JSX.Element {
  return (
    <section className="card" id="efficiency">
      <h2>Efficiency (weekly)</h2>
      {data.filtered_by === undefined ? null : (
        <p className="category">Filtered by: {data.filtered_by}</p>
      )}
      <div className="chart-grid-2">
        <div>
          <h3>USD per DONE session</h3>
          <LineChart
            format={formatUsd}
            label="USD per DONE session"
            series={[
              {
                label: "USD per DONE",
                points: points(data.done, "usd_per_done"),
              },
            ]}
          />
          <p className="caption">{data.captions.done}</p>
        </div>
        <div>
          <h3>DONE share of tagged sessions</h3>
          <LineChart
            format={formatShare}
            label="DONE share"
            series={[
              { label: "DONE share", points: points(data.done, "done_share") },
            ]}
          />
          <p className="caption">
            Untagged (pre-convention) sessions in range:{" "}
            {total(data.done, "untagged")}, excluded from both ratios.
          </p>
        </div>
        <div>
          <h3>USD per surviving commit</h3>
          <LineChart
            format={formatUsd}
            label="USD per surviving commit"
            series={[
              {
                label: "USD per survivor",
                points: points(data.commits, "usd_per_survivor"),
              },
            ]}
          />
          <p className="caption">
            {data.captions.commits} In range: {total(data.commits, "survived")}{" "}
            survived, {total(data.commits, "lost")} reverted/churned,{" "}
            {total(data.commits, "pending")} pending.
          </p>
        </div>
        <div>
          <h3>USD per estimated size unit (noisy)</h3>
          <LineChart
            format={(n) => `$${n.toFixed(3)}`}
            label="USD per estimated call"
            series={[
              {
                label: "USD per est. call",
                points: points(data.estimate, "usd_per_unit"),
              },
            ]}
          />
          <p className="caption">{data.captions.estimate}</p>
        </div>
      </div>
      {TABLES.map((table) => <WeeklyTable data={data} key={table.id} table={table} />)}
    </section>
  );
}
