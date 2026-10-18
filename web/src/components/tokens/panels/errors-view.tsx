import type { PanelView } from "../views.ts";

import { ErrorsPanel, type ErrorsPanelData } from "../groups/errors-panel.tsx";

export const view: PanelView = {
  name: "errors",
  order: 88,
  render: (data) => <ErrorsPanel data={data as ErrorsPanelData} />,
  title: "Errors",
};
