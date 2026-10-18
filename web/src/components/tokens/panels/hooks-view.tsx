import type { PanelView } from "../views.ts";

import { HooksPanel, type HooksPanelData } from "../groups/hooks-panel.tsx";

export const view: PanelView = {
  name: "hooks",
  order: 62,
  render: (data) => <HooksPanel data={data as HooksPanelData} />,
  title: "Hooks",
};
