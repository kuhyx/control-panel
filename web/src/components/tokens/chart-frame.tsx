// Shared chart geometry, axis and tooltip. Hand-rolled SVG rather than a chart
// library: a library would sit on the dependency-freshness treadmill for a
// handful of line and column charts.
//
// Colours are the design system's categorical ramp, used in a fixed order
// (cat-2, cat-3, cat-5): that triple passes the dataviz validator against both
// the dark and the light surface (CVD ΔE ≥ 16, normal ΔE ≥ 22); cat-3/cat-4
// adjacent did not.
export const SERIES_COLORS = [
  "var(--cat-2)",
  "var(--cat-3)",
  "var(--cat-5)",
] as const;

export function colorAt(index: number): string {
  return SERIES_COLORS[index % SERIES_COLORS.length] ?? SERIES_COLORS[0];
}

export const WIDTH = 640;
export const PAD = { bottom: 24, left: 52, right: 72, top: 16 } as const;
const TICKS = 4;
const NICE = [1, 2, 2.5, 5, 10] as const;

export function niceMax(value: number): number {
  if (value <= 0 || !Number.isFinite(value)) return 1;
  const raw = value / TICKS;
  const magnitude = 10 ** Math.floor(Math.log10(raw));
  let step = 10;
  for (const n of NICE) {
    if (n * magnitude >= raw) {
      step = n;
      break;
    }
  }
  return step * magnitude * TICKS;
}

export interface Frame {
  height: number;
  max: number;
  y: (value: number) => number;
}

export function makeFrame(max: number, height: number): Frame {
  const top = niceMax(max);
  const inner = height - PAD.top - PAD.bottom;
  return {
    height,
    max: top,
    y: (value) => PAD.top + inner - (value / top) * inner,
  };
}

export function YAxis({
  format,
  frame,
}: Readonly<{ format: (n: number) => string; frame: Frame }>): React.JSX.Element {
  const ticks = Array.from(
    { length: TICKS + 1 },
    (_, index) => (frame.max / TICKS) * index,
  );
  return (
    <g className="chart-axis">
      {ticks.map((tick) => {
        return (
          <g key={tick}>
            <line
              className="chart-grid"
              x1={PAD.left}
              x2={WIDTH - PAD.right}
              y1={frame.y(tick)}
              y2={frame.y(tick)}
            />
            <text textAnchor="end" x={PAD.left - 6} y={frame.y(tick) + 4}>
              {format(tick)}
            </text>
          </g>
        );
      })}
    </g>
  );
}

export function XLabels({
  frame,
  xAt,
  xs,
}: Readonly<{
  frame: Frame;
  xAt: (index: number) => number;
  xs: string[];
}>): React.JSX.Element {
  // First, middle and last only: dates are long, and the tooltip carries
  // every other one.
  const picks = [...new Set([0, Math.floor((xs.length - 1) / 2), xs.length - 1])];
  return (
    <g className="chart-axis">
      {picks
        .filter((index) => index >= 0)
        .map((index) => {
          return (
            <text
              key={index}
              textAnchor="middle"
              x={xAt(index)}
              y={frame.height - 6}
            >
              {xs[index]}
            </text>
          );
        })}
    </g>
  );
}

export function Legend({
  items,
}: Readonly<{
  items: { color: string; dashed?: boolean; label: string }[];
}>): null | React.JSX.Element {
  if (items.length < 2) return null;
  return (
    <ul className="chart-legend">
      {items.map((item) => {
        return (
          <li key={item.label}>
            <span
              aria-hidden="true"
              className={item.dashed === true ? "key key-texture" : "key"}
              style={{ background: item.color }}
            />
            {item.label}
          </li>
        );
      })}
    </ul>
  );
}

export function Tooltip({
  left,
  lines,
}: Readonly<{ left: number; lines: string[] }>): React.JSX.Element {
  return (
    <div
      className="chart-tooltip"
      role="status"
      style={{ left: `${((left / WIDTH) * 100).toFixed(1)}%` }}
    >
      {lines.map((line) => {
        return (
          <div key={line}>{line}</div>
        );
      })}
    </div>
  );
}

// Map a pointer position to the nearest slot index.
export function slotAt(
  event: React.MouseEvent<SVGRectElement>,
  count: number,
  xAt: (index: number) => number,
): number {
  const box = event.currentTarget.ownerSVGElement?.getBoundingClientRect();
  if (count === 0 || box === undefined || box.width === 0) return 0;
  const x = ((event.clientX - box.left) / box.width) * WIDTH;
  let best = 0;
  for (let index = 1; index < count; index += 1) {
    if (Math.abs(xAt(index) - x) < Math.abs(xAt(best) - x)) best = index;
  }
  return best;
}
