import type { Tables } from "../../../lib/tokens-types.ts";

import {
  formatCount,
  formatShare,
  formatUsd,
} from "../../../lib/tokens-api.ts";
import { type Column, ColumnChart } from "../column-chart.tsx";
import { type ColumnSpec, DataTable } from "../data-table.tsx";
import {
  countColumn,
  monoColumn,
  textColumn,
  usdColumn,
} from "./tools-columns.tsx";

interface SessionRow {
  key: string;
  length: number;
  prompt: string;
  usd: number;
}

interface BucketRow {
  bucket: string;
  mean_usd: null | number;
  sessions: number;
  total_usd: number;
}

interface PrefixRow {
  prefix: string;
  prompts: number;
  session_usd: number;
  sessions: number;
}

export interface PromptHabitsData {
  _tables?: Tables;
  caption: string;
  home: {
    session_share: null | number;
    sessions: number;
    usd: number;
    usd_share: null | number;
  };
  length_buckets: BucketRow[];
  prefixes: PrefixRow[];
  sessions: SessionRow[];
}

const BUCKET_COLUMNS: ColumnSpec<BucketRow>[] = [
  textColumn<BucketRow>("bucket", "opening prompt length (chars)"),
  countColumn<BucketRow>("sessions", "sessions"),
  usdColumn<BucketRow>("mean_usd", "mean session USD"),
  usdColumn<BucketRow>("total_usd", "total USD"),
];

const SESSION_COLUMNS: ColumnSpec<SessionRow>[] = [
  monoColumn<SessionRow>("key", "session"),
  textColumn<SessionRow>("prompt", "opening prompt"),
  countColumn<SessionRow>("length", "length", "chars (max 120 stored)"),
  usdColumn<SessionRow>("usd", "session USD"),
];

const PREFIX_COLUMNS: ColumnSpec<PrefixRow>[] = [
  monoColumn<PrefixRow>("prefix", "prefix"),
  countColumn<PrefixRow>("prompts", "prompts"),
  countColumn<PrefixRow>("sessions", "sessions"),
  usdColumn<PrefixRow>("session_usd", "those sessions' USD"),
];

function meanColumn(row: BucketRow): Column {
  return { x: row.bucket, y: row.mean_usd ?? 0 };
}

export function PromptHabitsPanel({
  data,
}: Readonly<{ data: PromptHabitsData }>): React.JSX.Element {
  const { home } = data;
  const tables = data._tables;
  return (
    <section className="card" id="prompt-habits">
      <h2>Prompt habits</h2>
      <ul aria-label="Prompt habits summary" className="tiles">
        <li className="tile">
          <span className="tile-count hero">{formatShare(home.usd_share)}</span>
          <span className="tile-label">
            of spend in sessions started from ~ ({formatUsd(home.usd)})
          </span>
        </li>
        <li className="tile">
          <span className="tile-count">{formatCount(home.sessions)}</span>
          <span className="tile-label">
            sessions from ~ ({formatShare(home.session_share)} of sessions)
          </span>
        </li>
      </ul>
      <p className="caption">{data.caption}</p>
      <ColumnChart
        columns={data.length_buckets.map((row) => meanColumn(row))}
        format={formatUsd}
        label="Mean session cost by opening prompt length"
      />
      <DataTable<BucketRow>
        columns={BUCKET_COLUMNS}
        id="length_buckets"
        meta={tables?.length_buckets}
        rowKey={(row) => row.bucket}
        rows={data.length_buckets}
        title="Opening prompt length vs session cost"
      />
      <DataTable<PrefixRow>
        columns={PREFIX_COLUMNS}
        id="prefixes"
        meta={tables?.prefixes}
        rowKey={(row) => row.prefix}
        rows={data.prefixes}
        title="Prompt prefixes"
      />
      <DataTable<SessionRow>
        columns={SESSION_COLUMNS}
        id="sessions"
        meta={tables?.sessions}
        rowKey={(row) => row.key}
        rows={data.sessions}
        title="Sessions by cost, with their opening prompt"
      />
    </section>
  );
}
