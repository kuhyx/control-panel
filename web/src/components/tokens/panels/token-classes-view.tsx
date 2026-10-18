import type { PanelView } from "../views.ts";

import {
  type TokenClassesData,
  TokenClassesPanel,
} from "../groups/token-classes-panel.tsx";

export const view: PanelView = {
  name: "token_classes",
  order: 66,
  render: (data) => <TokenClassesPanel data={data as TokenClassesData} />,
  title: "Token classes & cache",
};
