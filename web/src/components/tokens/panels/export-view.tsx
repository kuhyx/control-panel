import type { PanelView } from "../views.ts";

import { ExportPanel, type ExportPanelData } from "../groups/export-panel.tsx";

export const view: PanelView = {
  name: "export",
  order: 99,
  render: (data) => <ExportPanel data={data as ExportPanelData} />,
  title: "Raw rows (export)",
};
