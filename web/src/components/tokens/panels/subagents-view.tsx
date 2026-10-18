import type { PanelView } from "../views.ts";

import {
  SubagentsPanel,
  type SubagentsPanelData,
} from "../groups/subagents-panel.tsx";

export const view: PanelView = {
  name: "subagents",
  order: 74,
  render: (data) => <SubagentsPanel data={data as SubagentsPanelData} />,
  title: "Subagents",
};
