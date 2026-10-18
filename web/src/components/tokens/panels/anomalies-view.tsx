import type { PanelView } from "../views.ts";

import {
  AnomaliesPanel,
  type AnomaliesPanelData,
} from "../groups/anomalies-panel.tsx";

export const view: PanelView = {
  name: "anomalies",
  order: 86,
  render: (data) => <AnomaliesPanel data={data as AnomaliesPanelData} />,
  title: "Anomalies",
};
