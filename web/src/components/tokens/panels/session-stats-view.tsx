import type { PanelView } from "../views.ts";

import {
  type SessionStatsData,
  SessionStatsPanel,
} from "../groups/session-stats-panel.tsx";

export const view: PanelView = {
  name: "session_stats",
  order: 76,
  render: (data) => <SessionStatsPanel data={data as SessionStatsData} />,
  title: "Session stats",
};
