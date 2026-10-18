import type { LeversPanel as Data } from "../../../lib/tokens-types.ts";
import type { PanelView } from "../views.ts";

import { LeversPanel } from "../levers-panel.tsx";

export const view: PanelView = {
  name: "levers",
  order: 40,
  render: (data) => <LeversPanel data={data as Data} />,
  title: "Levers",
};
