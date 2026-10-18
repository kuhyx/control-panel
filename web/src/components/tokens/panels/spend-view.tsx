import type { OverviewPanel } from "../../../lib/tokens-types.ts";
import type { PanelView } from "../views.ts";

import { SpendPanel } from "../spend-panel.tsx";

export const view: PanelView = {
  name: "overview",
  order: 10,
  render: (data, { index }) => {
    return (
      <SpendPanel
        data={data as OverviewPanel}
        index={index}
        snapshotMetrics={index.snapshot_metrics}
      />
    );
  },
  title: "Spend",
};
