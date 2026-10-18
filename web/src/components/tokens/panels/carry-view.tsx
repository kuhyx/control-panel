import type { PanelView } from "../views.ts";

import { CarryPanel, type CarryPanelData } from "../groups/carry-panel.tsx";

export const view: PanelView = {
  name: "carry",
  order: 60,
  render: (data) => <CarryPanel data={data as CarryPanelData} />,
  title: "Carry cost",
};
