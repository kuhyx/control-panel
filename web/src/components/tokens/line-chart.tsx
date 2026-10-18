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

export interface Point {
  x: string;
  y: null | number;
}

function isPlotted(point: Point): point is { x: string; y: number } {
  return point.y !== null;
}

export interface LineSeries {
  dots?: boolean;
  label: string;
  points: Point[];
}

export interface ReferenceLine {
  label: string;
  y: number;
}

export interface Marker {
  label: string;
  x: string;
}

const HEIGHT = 180;

// Plain code-unit order, as `Array#sort()` without a comparator gives: ISO
// dates and week labels sort correctly that way, with no locale in play.
function byCodeUnit(a: string, b: string): number {
  return a < b ? -1 : Number(a > b);
}

function pathFor(
  points: Point[],
  xAt: (x: string) => number,
  y: (v: number) => number,
): string {
  let path = "";
  let pen = "M";
  for (const point of points) {
    if (point.y === null) {
      pen = "M";
      continue;
    }
    path += `${pen}${xAt(point.x).toFixed(1)},${y(point.y).toFixed(1)}`;
    pen = "L";
  }
  return path;
}

// Line chart over an ordinal x axis (ISO dates sort as strings). Reference
// lines are horizontal (baseline / predicted); markers are vertical (applied
// date). Hover shows a crosshair and every series' value at that x.
export function LineChart({
  format,
  label,
  markers = [],
  refLines: referenceLines = [],
  series,
  titled = false,
}: Readonly<{
  format: (n: number) => string;
  label: string;
  markers?: Marker[];
  refLines?: ReferenceLine[];
  series: LineSeries[];
  // Show `label` as a visible caption (panels without their own heading).
  titled?: boolean;
}>): React.JSX.Element {
  const [hover, setHover] = useState<null | number>(null);
  const seen = new Set(series.flatMap((s) => s.points.map((p) => p.x)));
  for (const marker of markers) seen.add(marker.x);
  const xs = [...seen].toSorted(byCodeUnit);
  const values = [
    ...series.flatMap((s) => s.points.map((p) => p.y ?? 0)),
    ...referenceLines.map((r) => r.y),
  ];
  const frame = makeFrame(Math.max(0, ...values), HEIGHT);
  const span = WIDTH - PAD.left - PAD.right;
  const xAtIndex = (index: number): number =>
    PAD.left + (xs.length > 1 ? (index / (xs.length - 1)) * span : span / 2);
  const xAt = (x: string): number => xAtIndex(xs.indexOf(x));
  const hoveredX = hover === null ? null : xs[hover];
  const tip =
    hoveredX === undefined || hoveredX === null
      ? []
      : [
          hoveredX,
          ...series.flatMap((s) => {
            const found = s.points.find((p) => p.x === hoveredX);
            return found?.y == null ? [] : `${s.label}: ${format(found.y)}`;
          }),
          ...markers.filter((m) => m.x === hoveredX).map((m) => m.label),
        ];
  return (
    <figure className="chart">
      {titled && <figcaption className="chart-title">{label}</figcaption>}
      <Legend
        items={series.map((s, index) => {
          return {
            color: colorAt(index),
            label: s.label,
          };
        })}
      />
      <svg aria-label={label} role="img" viewBox={`0 0 ${WIDTH} ${HEIGHT}`}>
        <YAxis format={format} frame={frame} />
        <XLabels frame={frame} xAt={xAtIndex} xs={xs} />
        {referenceLines.map((reference) => {
          return (
            <g className="chart-ref" key={reference.label}>
              <line
                x1={PAD.left}
                x2={WIDTH - PAD.right}
                y1={frame.y(reference.y)}
                y2={frame.y(reference.y)}
              />
              <text x={WIDTH - PAD.right + 4} y={frame.y(reference.y) + 4}>
                {reference.label}
              </text>
            </g>
          );
        })}
        {markers.map((marker) => {
          return (
            <g className="chart-marker" key={`${marker.x}${marker.label}`}>
              <line
                x1={xAt(marker.x)}
                x2={xAt(marker.x)}
                y1={PAD.top}
                y2={HEIGHT - PAD.bottom}
              />
              <text textAnchor="middle" x={xAt(marker.x)} y={PAD.top - 4}>
                {marker.label}
              </text>
            </g>
          );
        })}
        {series.map((s, index) => {
          const color = colorAt(index);
          return s.dots === true ? (
            <g key={s.label}>
              {s.points
                .filter((p) => isPlotted(p))
                .map((p) => {
                  return (
                    <circle
                      className="chart-dot"
                      cx={xAt(p.x)}
                      cy={frame.y(p.y)}
                      fill={color}
                      key={p.x}
                      r={4}
                    />
                  );
                })}
            </g>
          ) : (
            <path
              className="chart-line"
              d={pathFor(s.points, xAt, frame.y)}
              key={s.label}
              stroke={color}
            />
          );
        })}
        {hover !== null && (
          <line
            className="chart-crosshair"
            x1={xAtIndex(hover)}
            x2={xAtIndex(hover)}
            y1={PAD.top}
            y2={HEIGHT - PAD.bottom}
          />
        )}
        <rect
          className="chart-hit"
          height={HEIGHT}
          onMouseLeave={() => {
            setHover(null);
          }}
          onMouseMove={(event) => {
            setHover(slotAt(event, xs.length, xAtIndex));
          }}
          width={WIDTH}
          x={0}
          y={0}
        />
      </svg>
      {hover !== null && tip.length > 0 && (
        <Tooltip left={xAtIndex(hover)} lines={tip} />
      )}
    </figure>
  );
}
