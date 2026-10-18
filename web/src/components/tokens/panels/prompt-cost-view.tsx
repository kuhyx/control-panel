import type { PanelView } from "../views.ts";

import {
  PromptCostPanel,
  type PromptCostPanelData,
} from "../groups/prompt-cost-panel.tsx";

export const view: PanelView = {
  name: "prompts",
  order: 82,
  render: (data) => <PromptCostPanel data={data as PromptCostPanelData} />,
  title: "Cost per prompt",
};
