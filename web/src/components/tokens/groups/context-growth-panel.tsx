import type { Tables } from "../../../lib/tokens-types.ts";

import { formatCount } from "../../../lib/tokens-api.ts";
import { ColumnChart } from "../column-chart.tsx";
import { LineChart } from "../line-chart.tsx";
import {
  type CrossingRow,
  GrowthTables,
  type HandoffRow,
} from "./context-growth-tables.tsx";

interface Curve {
  // Curves of one chart share their sampled call indices (see _context_growth).
  chart: number;
  key: string;
  max_context: number;
  points: { call: number; context: number }[];
  title: string;
  usd: number;
}

export interface ContextGrowthData {
  _tables?: Tables;
  caption: string;
  crossings: CrossingRow[];
  growth: Curve[];
  handoffs: HandoffRow[];
  histogram: { bucket: string; calls: number; usd: number }[];
  percentiles: Record<"p50" | "p90" | "p99", null | number>;
}

// The chart's x axis sorts as text: pad call indices so 10 follows 9.
const PAD = 6;

// The backend groups curves three per chart (one colour each) on a shared grid.
function charts(curves: Curve[]): { curves: Curve[]; first: number }[] {
  const groups = new Map<number, Curve[]>();
  for (const curve of curves) {
    groups.set(curve.chart, [...(groups.get(curve.chart) ?? []), curve]);
  }
  let first = 1;
  return groups
    .values()
    .map((group) => {
      const chart = { curves: group, first };
      first += group.length;
      return chart;
    })
    .toArray();
}

function curveLabel(curve: Curve): string {
  const short = curve.key.slice(0, 8);
  return curve.title === "" ? short : `${short} ${curve.title.slice(0, 40)}`;
}

export function ContextGrowthPanel({
  data,
}: Readonly<{ data: ContextGrowthData }>): React.JSX.Element {
  const p = data.percentiles;
  const groups = charts(data.growth);
  return (
    <section className="card" id="context-growth">
      <h2>Context size</h2>
      <ul aria-label="Context percentiles" className="tiles">
        {(["p50", "p90", "p99"] as const).map((name) => {
          const value = p[name];
          return (
            <li className="tile" key={name}>
              <span className="tile-count">
                {value === null ? "—" : formatCount(value)}
              </span>
              <span className="tile-label">{name} context (tokens)</span>
            </li>
          );
        })}
      </ul>
      <p className="caption">{data.caption}</p>
      <ColumnChart
        columns={data.histogram.map((b) => ({ x: b.bucket, y: b.calls }))}
        format={formatCount}
        label="Calls per context size"
        titled
      />
      {groups.map(({ curves: group, first }) => {
        const name = `Context growth, sessions ${String(first)}-${String(first + group.length - 1)}`;
        return (
          <LineChart
            format={formatCount}
            key={name}
            label={name}
            series={group.map((curve) => {
              return {
                label: curveLabel(curve),
                points: curve.points.map((pt) => {
                  return {
                    x: String(pt.call).padStart(PAD, "0"),
                    y: pt.context,
                  };
                }),
              };
            })}
            titled
          />
        );
      })}
      <GrowthTables
        crossings={data.crossings}
        handoffs={data.handoffs}
        tables={data._tables}
      />
    </section>
  );
}
