import type { PanelView } from "../views.ts";

import {
  type SpendMoreData,
  SpendMorePanel,
} from "../groups/spend-more-panel.tsx";

export const view: PanelView = {
  name: "spend_more",
  order: 72,
  render: (data) => <SpendMorePanel data={data as SpendMoreData} />,
  title: "Spend breakdown",
};
