import type { PanelView } from "../views.ts";

import {
  type PromptHabitsData,
  PromptHabitsPanel,
} from "../groups/prompt-habits-panel.tsx";

export const view: PanelView = {
  name: "prompt_habits",
  order: 90,
  render: (data) => <PromptHabitsPanel data={data as PromptHabitsData} />,
  title: "Prompt habits",
};
