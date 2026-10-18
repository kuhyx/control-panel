import { useState } from "react";

import {
  colorAt,
  Legend,
  makeFrame,
  PAD,
  slotAt,
  Tooltip,
  WIDTH,
  XLabels,
  YAxis,
} from "./chart-frame.tsx";

export interface Column {
  // An aggregate-only column (no per-session detail behind it) is drawn
  // hatched, so the difference never rests on colour alone.
  aggregate?: boolean;
  note?: string;
  x: string;
  y: number;
}

const HEIGHT = 180;
const MAX_BAR = 24;
const GAP = 2;
const RADIUS = 4;

// A column with a rounded data end and a square baseline.
function barPath(x: number, top: number, width: number, base: number): string {
  const radius = Math.min(RADIUS, width / 2, Math.max(0, base - top));
  return [
    `M${x},${base}`,
    `V${top + radius}`,
    `Q${x},${top} ${x + radius},${top}`,
    `H${x + width - radius}`,
    `Q${x + width},${top} ${x + width},${top + radius}`,
    `V${base}Z`,
  ].join("");
}

function tipLines(
  column: Column,
  format: (n: number) => string,
  aggregateLabel: string,
): string[] {
  const suffix = column.aggregate === true ? ` (${aggregateLabel})` : "";
  return [
    column.x,
    `${format(column.y)}${suffix}`,
    ...(column.note === undefined ? [] : [column.note]),
  ];
}

export function ColumnChart({
  aggregateLabel = "aggregate only",
  columns,
  detailLabel = "per-session detail",
  format,
  label,
}: Readonly<{
  aggregateLabel?: string;
  columns: Column[];
  detailLabel?: string;
  format: (n: number) => string;
  label: string;
}>): React.JSX.Element {
  const [hover, setHover] = useState<null | number>(null);
  const frame = makeFrame(Math.max(0, ...columns.map((c) => c.y)), HEIGHT);
  const span = WIDTH - PAD.left - PAD.right;
  const slot = span / Math.max(columns.length, 1);
  const width = Math.max(1, Math.min(MAX_BAR, slot - GAP));
  const xAt = (index: number): number => PAD.left + slot * index + slot / 2;
  const base = frame.y(0);
  const color = colorAt(0);
  const hasAggregate = columns.some((c) => c.aggregate === true);
  const hovered = hover === null ? undefined : columns[hover];
  return (
    <figure className="chart">
      <Legend
        items={
          hasAggregate
            ? [
                { color, label: detailLabel },
                { color, dashed: true, label: aggregateLabel },
              ]
            : []
        }
      />
      <svg aria-label={label} role="img" viewBox={`0 0 ${WIDTH} ${HEIGHT}`}>
        <defs>
          <pattern
            height="6"
            id="hatch"
            patternTransform="rotate(45)"
            patternUnits="userSpaceOnUse"
            width="6"
          >
            <rect fill={color} height="6" opacity="0.35" width="6" />
            <line stroke={color} strokeWidth="2" x1="0" x2="0" y1="0" y2="6" />
          </pattern>
        </defs>
        <YAxis format={format} frame={frame} />
        <XLabels frame={frame} xAt={xAt} xs={columns.map((c) => c.x)} />
        {columns.map((column, index) => {
          return (
            <path
              className={hover === index ? "chart-bar active" : "chart-bar"}
              d={barPath(xAt(index) - width / 2, frame.y(column.y), width, base)}
              fill={column.aggregate === true ? "url(#hatch)" : color}
              key={`${column.x}${String(column.aggregate)}`}
            />
          );
        })}
        <rect
          className="chart-hit"
          height={HEIGHT}
          onMouseLeave={() => {
            setHover(null);
          }}
          onMouseMove={(event) => {
            setHover(slotAt(event, columns.length, xAt));
          }}
          width={WIDTH}
          x={0}
          y={0}
        />
      </svg>
      {hover !== null && hovered !== undefined && (
        <Tooltip
          left={xAt(hover)}
          lines={tipLines(hovered, format, aggregateLabel)}
        />
      )}
    </figure>
  );
}
