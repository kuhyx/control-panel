import type { ContextPanel as Data } from "../../../lib/tokens-types.ts";
import type { PanelView } from "../views.ts";

import { ContextPanel } from "../context-panel.tsx";

export const view: PanelView = {
  name: "context",
  order: 50,
  render: (data) => <ContextPanel data={data as Data} />,
  title: "Context files",
};
