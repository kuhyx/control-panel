import type { PanelView } from "../views.ts";

import { PrefixPanel, type PrefixPanelData } from "../groups/prefix-panel.tsx";

export const view: PanelView = {
  name: "prefix",
  order: 64,
  render: (data) => <PrefixPanel data={data as PrefixPanelData} />,
  title: "Standing prefix",
};
