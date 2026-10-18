import type { Tables } from "../../../lib/tokens-types.ts";

import {
  formatCount,
  formatShare,
  formatUsd,
} from "../../../lib/tokens-api.ts";
import { LineChart } from "../line-chart.tsx";
import {
  type ClassDay,
  ClassTables,
  type CompactionRow,
  type WasteRow,
} from "./token-classes-tables.tsx";

export interface TokenClassesData {
  _tables?: Tables;
  caption: string;
  compactions: CompactionRow[];
  daily: ClassDay[];
  prices_source: string;
  totals: {
    cache_read: number;
    cold_start_usd: number;
    cold_starts: number;
    compaction_usd: number;
    compactions: number;
    cw_1h: number;
    cw_5m: number;
    hit_ratio: null | number;
    input: number;
    output: number;
    pending_tokens: number;
    spend_usd: number;
    unsplit: number;
    usd: number;
    waste_tokens: number;
    waste_usd: number;
  };
  waste: WasteRow[];
}

function series(
  daily: ClassDay[],
  label: string,
  get: (d: ClassDay) => null | number,
) {
  return { label, points: daily.map((d) => ({ x: d.day, y: get(d) })) };
}

function Tile({
  hero = false,
  label,
  value,
}: Readonly<{
  hero?: boolean;
  label: string;
  value: string;
}>): React.JSX.Element {
  return (
    <li className="tile">
      <span className={hero ? "tile-count hero" : "tile-count"}>{value}</span>
      <span className="tile-label">{label}</span>
    </li>
  );
}

export function TokenClassesPanel({
  data,
}: Readonly<{ data: TokenClassesData }>): React.JSX.Element {
  const { daily, totals } = data;
  return (
    <section className="card" id="token-classes">
      <h2>Token classes &amp; cache</h2>
      <ul aria-label="Cache summary" className="tiles">
        <Tile
          hero
          label="cache hit ratio"
          value={formatShare(totals.hit_ratio)}
        />
        <Tile
          label={`never re-read (${formatCount(totals.waste_tokens)} tokens; ${formatCount(totals.pending_tokens)} pending)`}
          value={formatUsd(totals.waste_usd)}
        />
        <Tile
          label={`cold starts (${formatUsd(totals.cold_start_usd)})`}
          value={formatCount(totals.cold_starts)}
        />
        <Tile
          label={`${formatCount(totals.compactions)} compactions (est.)`}
          value={formatUsd(totals.compaction_usd)}
        />
        <Tile
          label={`classes priced, of ${formatUsd(totals.spend_usd)} recorded`}
          value={formatUsd(totals.usd)}
        />
      </ul>
      <p className="caption">{data.caption}</p>
      <LineChart
        format={formatUsd}
        label="Cost per class per day"
        series={[
          series(daily, "cache read", (d) => d.cache_read_usd),
          series(
            daily,
            "cache write",
            (d) => d.cw_5m_usd + d.cw_1h_usd + d.unsplit_usd,
          ),
          series(daily, "input + output", (d) => d.input_usd + d.output_usd),
        ]}
        titled
      />
      <LineChart
        format={formatCount}
        label="Cache-write tokens per day"
        series={[
          series(daily, "5m", (d) => d.cw_5m),
          series(daily, "1h", (d) => d.cw_1h),
          series(daily, "unsplit (priced as 5m)", (d) => d.unsplit),
        ]}
        titled
      />
      <LineChart
        format={formatShare}
        label="Cache hit ratio per day"
        series={[series(daily, "hit ratio", (d) => d.hit_ratio)]}
        titled
      />
      <ClassTables
        compactions={data.compactions}
        daily={daily}
        tables={data._tables}
        waste={data.waste}
      />
      <p className="caption">Prices: {data.prices_source}</p>
    </section>
  );
}
