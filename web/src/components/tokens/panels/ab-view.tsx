import type { AbPanel as Data } from "../../../lib/tokens-types.ts";
import type { PanelView } from "../views.ts";

import { AbPanel } from "../ab-panel.tsx";

export const view: PanelView = {
  name: "ab",
  order: 35,
  render: (data) => <AbPanel data={data as Data} />,
  title: "A/B judgment subagents",
};
