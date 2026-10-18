import { formatCount, formatUsd } from "../../../lib/tokens-api.ts";

// Weekday x hour grid of spend. One sequential hue (the first series colour,
// cat-2) with opacity rising with the value: the design tokens have no
// sequential ramp, and a single hue keeps "more" readable in light and dark.
// The numbers are in the heatmap table next to it, so nothing rests on colour.

export interface HeatCell {
  calls: number;
  hour: number;
  usd: number;
  // 0 = Monday.
  weekday: number;
}

export const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const HOURS = Array.from({ length: 24 }, (_, hour) => hour);
const CELL_W = 22;
const CELL_H = 18;
const LEFT = 36;
const TOP = 16;
const FLOOR = 0.12; // the faintest non-empty cell stays visible
const EMPTY = 0.04;

export function cellOpacity(usd: number, max: number): number {
  return usd <= 0 || max <= 0 ? EMPTY : FLOOR + (1 - FLOOR) * (usd / max);
}

export function Heatmap({
  cells,
}: Readonly<{ cells: HeatCell[] }>): React.JSX.Element {
  const byCell = new Map(cells.map((c) => [`${c.weekday}|${c.hour}`, c]));
  const max = Math.max(0, ...cells.map((c) => c.usd));
  const width = LEFT + HOURS.length * CELL_W;
  const height = TOP + WEEKDAYS.length * CELL_H;
  return (
    <figure className="chart">
      <svg
        aria-label="Spend by weekday and hour"
        role="img"
        viewBox={`0 0 ${String(width)} ${String(height)}`}
      >
        <g className="chart-axis">
          {HOURS.filter((hour) => hour % 3 === 0).map((hour) => {
            return (
              <text
                key={hour}
                textAnchor="middle"
                x={LEFT + hour * CELL_W + CELL_W / 2}
                y={TOP - 4}
              >
                {String(hour).padStart(2, "0")}
              </text>
            );
          })}
          {WEEKDAYS.map((name, day) => {
            return (
              <text key={name} x={0} y={TOP + day * CELL_H + CELL_H - 5}>
                {name}
              </text>
            );
          })}
        </g>
        {WEEKDAYS.flatMap((name, day) => {
          return HOURS.map((hour) => {
            const cell = byCell.get(`${day}|${hour}`);
            const usd = cell?.usd ?? 0;
            return (
              <rect
                fill="var(--cat-2)"
                fillOpacity={cellOpacity(usd, max)}
                height={CELL_H - 2}
                key={`${name}${hour}`}
                rx={2}
                width={CELL_W - 2}
                x={LEFT + hour * CELL_W}
                y={TOP + day * CELL_H}
              >
                <title>
                  {`${name} ${String(hour).padStart(2, "0")}:00 — ${formatUsd(usd)} (${formatCount(cell?.calls ?? 0)} calls)`}
                </title>
              </rect>
            );
          });
        })}
      </svg>
    </figure>
  );
}
