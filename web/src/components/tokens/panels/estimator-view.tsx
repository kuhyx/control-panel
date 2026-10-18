import type { PanelView } from "../views.ts";

import {
  EstimatorPanel,
  type EstimatorPanelData,
} from "../groups/estimator-panel.tsx";

export const view: PanelView = {
  name: "estimator",
  order: 84,
  render: (data) => <EstimatorPanel data={data as EstimatorPanelData} />,
  title: "Task-size estimator",
};
