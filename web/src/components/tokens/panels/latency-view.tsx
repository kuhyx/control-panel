import type { PanelView } from "../views.ts";

import { type LatencyData, LatencyPanel } from "../groups/latency-panel.tsx";

export const view: PanelView = {
  name: "latency",
  order: 78,
  render: (data) => <LatencyPanel data={data as LatencyData} />,
  title: "Latency",
};
