import type { PanelView } from "../views.ts";

import { type OutputData, OutputPanel } from "../groups/output-panel.tsx";

export const view: PanelView = {
  name: "output",
  order: 80,
  render: (data) => <OutputPanel data={data as OutputData} />,
  title: "Output",
};
