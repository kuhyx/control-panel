import type { PanelView } from "../views.ts";

import { ToolsPanel, type ToolsPanelData } from "../groups/tools-panel.tsx";

export const view: PanelView = {
  name: "tools",
  order: 70,
  render: (data) => <ToolsPanel data={data as ToolsPanelData} />,
  title: "Tools",
};
