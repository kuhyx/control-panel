import type { PanelView } from "../views.ts";

import {
  type ContextGrowthData,
  ContextGrowthPanel,
} from "../groups/context-growth-panel.tsx";

export const view: PanelView = {
  name: "context_growth",
  order: 68,
  render: (data) => <ContextGrowthPanel data={data as ContextGrowthData} />,
  title: "Context size",
};
