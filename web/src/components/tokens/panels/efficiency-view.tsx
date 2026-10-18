import type { EfficiencyPanel as Data } from "../../../lib/tokens-types.ts";
import type { PanelView } from "../views.ts";

import { EfficiencyPanel } from "../efficiency-panel.tsx";

export const view: PanelView = {
  name: "efficiency",
  order: 30,
  render: (data) => <EfficiencyPanel data={data as Data} />,
  title: "Efficiency",
};
