import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { colorAt, Legend, niceMax, slotAt } from "./chart-frame.tsx";
import { ColumnChart } from "./column-chart.tsx";
import { CsvButton, toCsv } from "./csv.tsx";
import { LineChart } from "./line-chart.tsx";

const usd = (n: number): string => `$${n.toFixed(2)}`;

// jsdom lays nothing out, so give the chart's <svg> a real 640px-wide box
// (one SVG unit per pixel) and hover at an x in chart units.
function hoverAt(container: HTMLElement, x: number): void {
  const svg = container.querySelector("svg");
  if (svg !== null) {
    vi.spyOn(svg, "getBoundingClientRect").mockReturnValue({
      left: 0,
      width: 640,
    } as DOMRect);
  }
  const hit = container.querySelector(".chart-hit");
  if (hit !== null) fireEvent.mouseMove(hit, { clientX: x });
}

function leave(container: HTMLElement): void {
  const hit = container.querySelector(".chart-hit");
  if (hit !== null) fireEvent.mouseLeave(hit);
}

describe("chart frame", () => {
  it("cycles the categorical colours and falls back for a bad index", () => {
    expect(colorAt(0)).toBe("var(--cat-2)");
    expect(colorAt(4)).toBe("var(--cat-3)");
    expect(colorAt(-1)).toBe("var(--cat-2)");
  });

  it("rounds the axis maximum up to a nice step", () => {
    expect(niceMax(0)).toBe(1);
    expect(niceMax(Infinity)).toBe(1);
    expect(niceMax(7)).toBe(8);
    expect(niceMax(37)).toBe(40);
  });

  it("hides a single-item legend", () => {
    const { container } = render(<Legend items={[{ color: "red", label: "a" }]} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("returns slot 0 when the pointer has no SVG to measure against", () => {
    const event = {
      clientX: 10,
      currentTarget: { ownerSVGElement: null },
    } as unknown as React.MouseEvent<SVGRectElement>;
    expect(slotAt(event, 3, (index) => index)).toBe(0);
  });
});

describe("ColumnChart", () => {
  const columns = [
    { aggregate: true, note: "3 sessions", x: "2026-09-01", y: 5 },
    { x: "2026-09-02", y: 10 },
    { x: "2026-09-03", y: 2 },
  ];

  it("shows a hatched legend and a tooltip for the hovered column", () => {
    const { container } = render(
      <ColumnChart aggregateLabel="estimate" columns={columns} format={usd} label="Spend" />,
    );
    expect(screen.getByText("per-session detail")).toBeInTheDocument();
    expect(container.querySelector('[fill="url(#hatch)"]')).not.toBeNull();
    hoverAt(container, 482);
    expect(screen.getByRole("status")).toHaveTextContent("2026-09-03$2.00");
    expect(container.querySelector(".chart-bar.active")).not.toBeNull();
    hoverAt(container, 138);
    expect(screen.getByRole("status")).toHaveTextContent("$5.00 (estimate)3 sessions");
    leave(container);
    expect(screen.queryByRole("status")).toBeNull();
  });

  it("uses the default labels and lands at slot 0 on an unmeasured chart", () => {
    const { container } = render(
      <ColumnChart
        columns={[{ aggregate: true, x: "a", y: 1 }, { x: "b", y: 2 }]}
        detailLabel="detail"
        format={usd}
        label="Default"
      />,
    );
    expect(screen.getByText("aggregate only")).toBeInTheDocument();
    const hit = container.querySelector(".chart-hit");
    if (hit !== null) fireEvent.mouseMove(hit, { clientX: 300 });
    expect(screen.getByRole("status")).toHaveTextContent("a$1.00 (aggregate only)");
  });

  it("draws nothing to hover over when empty", () => {
    const { container } = render(<ColumnChart columns={[]} format={usd} label="Empty" />);
    hoverAt(container, 100);
    expect(screen.queryByRole("status")).toBeNull();
  });
});

describe("LineChart", () => {
  const series = [
    {
      label: "daily",
      points: [
        { x: "2026-09-02", y: 2 },
        { x: "2026-09-01", y: 1 },
        { x: "2026-09-03", y: null },
        { x: "2026-09-04", y: 4 },
      ],
    },
    { dots: true, label: "snapshot", points: [{ x: "2026-09-03", y: 3 }, { x: "2026-09-04", y: null }] },
  ];

  it("plots lines, dots, reference lines and markers, with a crosshair tooltip", () => {
    const { container } = render(
      <LineChart
        format={usd}
        label="Per call"
        markers={[{ label: "applied", x: "2026-09-05" }]}
        refLines={[{ label: "baseline", y: 2.5 }]}
        series={series}
      />,
    );
    // The null y lifts the pen: two "M" moves, joined by "L" segments.
    const d = container.querySelector(".chart-line")?.getAttribute("d") ?? "";
    expect(d.split("M")).toHaveLength(3);
    expect(d).toContain("L");
    expect(container.querySelectorAll(".chart-dot")).toHaveLength(1);
    expect(screen.getByText("baseline")).toBeInTheDocument();
    // Five x slots across 516 units: the last (the marker) sits at x=568.
    hoverAt(container, 568);
    expect(container.querySelector(".chart-crosshair")).not.toBeNull();
    expect(screen.getByRole("status")).toHaveTextContent("2026-09-05applied");
    hoverAt(container, 52);
    expect(screen.getByRole("status")).toHaveTextContent("2026-09-01daily: $1.00");
    hoverAt(container, 310);
    expect(screen.getByRole("status")).toHaveTextContent("2026-09-03snapshot: $3.00");
    leave(container);
    expect(container.querySelector(".chart-crosshair")).toBeNull();
  });

  it("centres a single point and shows no tooltip over an empty chart", () => {
    const { container, rerender } = render(
      <LineChart format={usd} label="One" series={[{ label: "a", points: [{ x: "d", y: 1 }] }]} />,
    );
    expect(container.querySelector(".chart-line")?.getAttribute("d")).toMatch(/^M310\.0,/);
    rerender(<LineChart format={usd} label="None" series={[]} />);
    hoverAt(container, 10);
    expect(screen.queryByRole("status")).toBeNull();
  });
});

describe("CSV export", () => {
  it("quotes cells with commas, quotes or newlines and serialises objects", () => {
    const rows = [
      { a: 'say "hi", ok', b: 1, c: null, d: { k: true } },
      { a: "line\nbreak", b: false, c: undefined, d: [1] },
    ];
    expect(toCsv(rows, ["a", "b", "c", "d"])).toBe(
      'a,b,c,d\n"say ""hi"", ok",1,,"{""k"":true}"\n"line\nbreak",false,,[1]',
    );
  });

  it("offers the CSV as a data-URL download", () => {
    render(<CsvButton columns={["a"]} name="x.csv" rows={[{ a: "v" }]} />);
    const link = screen.getByRole("link", { name: "CSV" });
    expect(link).toHaveAttribute("download", "x.csv");
    expect(link).toHaveAttribute("href", "data:text/csv;charset=utf-8,a%0Av");
  });
});
