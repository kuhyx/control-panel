import type { SessionsPanel as Data } from "../../../lib/tokens-types.ts";
import type { PanelView } from "../views.ts";

import { SessionsPanel } from "../sessions-panel.tsx";

export const view: PanelView = {
  name: "sessions",
  order: 45,
  render: (data) => <SessionsPanel data={data as Data} />,
  title: "Sessions",
};
