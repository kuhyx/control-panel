import type { Tables } from "../../../lib/tokens-types.ts";

import { formatShare, formatUsd } from "../../../lib/tokens-api.ts";
import { LineChart } from "../line-chart.tsx";
import { type ChunkRow, ChunkTable } from "./chunk-table.tsx";

type Bucket =
  | "attachments"
  | "context_reads"
  | "families"
  | "hooks"
  | "images"
  | "mcp"
  | "pasted_images"
  | "rereads"
  | "skills"
  | "web";

export type CarryPanelData = Record<Bucket, ChunkRow[]> & {
  _tables?: Tables;
  caption: string;
  daily: { context_usd: number; day: string; results_usd: number }[];
  totals: { carry_total_usd: number; spend_usd: number };
};

const BUCKETS: { id: Bucket; title: string }[] = [
  { id: "mcp", title: "MCP servers / tools" },
  { id: "skills", title: "Skill loads" },
  { id: "hooks", title: "Hook-injected context, per hook" },
  {
    id: "context_reads",
    title: "Memory / rules / CLAUDE.md / skill-file reads",
  },
  {
    id: "attachments",
    title: "Harness attachments (reminders, listings, nested CLAUDE.md)",
  },
  { id: "images", title: "Images in tool results" },
  { id: "pasted_images", title: "Pasted images" },
  { id: "rereads", title: "Top re-read paths" },
  { id: "web", title: "WebFetch / WebSearch" },
];

export function CarryPanel({
  data,
}: Readonly<{ data: CarryPanelData }>): React.JSX.Element {
  const { totals } = data;
  const share =
    totals.spend_usd > 0 ? totals.carry_total_usd / totals.spend_usd : null;
  return (
    <section className="card" id="carry">
      <h2>Carry cost (what context costs while it stays)</h2>
      <ul aria-label="Carry summary" className="tiles">
        <li className="tile">
          <span className="tile-count hero">
            {formatUsd(totals.carry_total_usd)}
          </span>
          <span className="tile-label">creation + carry in range</span>
        </li>
        <li className="tile">
          <span className="tile-count">{formatShare(share)}</span>
          <span className="tile-label">
            of {formatUsd(totals.spend_usd)} spend
          </span>
        </li>
      </ul>
      <p className="caption">{data.caption}</p>
      <LineChart
        format={formatUsd}
        label="Carry cost per day"
        series={[
          {
            label: "tool results",
            points: data.daily.map((d) => ({ x: d.day, y: d.results_usd })),
          },
          {
            label: "hooks, attachments, images",
            points: data.daily.map((d) => ({ x: d.day, y: d.context_usd })),
          },
        ]}
      />
      <ChunkTable
        id="families"
        rows={data.families}
        tables={data._tables}
        title="By Bash command family / tool"
        withCalls
      />
      {BUCKETS.map((bucket) => {
        return (
          <ChunkTable
            id={bucket.id}
            key={bucket.id}
            rows={data[bucket.id]}
            tables={data._tables}
            title={bucket.title}
          />
        );
      })}
    </section>
  );
}
