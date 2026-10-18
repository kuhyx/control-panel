// Every panel registers itself: a file `panels/<group>-view.tsx` exporting
// `view` is picked up here at build time, so adding a group touches no shared
// file. Each view fetches its own panel (see LazyPanel), so one failing panel
// never blanks the page and a table change refetches only its own panel.
import type { TokensIndex } from "../../lib/tokens-types.ts";

export interface PageContext {
  index: TokensIndex;
}

export interface PanelView {
  // Backend panel name: GET /api/tokens/panel/<name>.
  name: string;
  // Position on the page (ascending).
  order: number;
  render: (data: unknown, page: PageContext) => React.JSX.Element;
  // Named in copied table headers ("View: <title> / <table>").
  title: string;
}

interface ViewModule {
  view: PanelView;
}

export function sortViews(modules: Record<string, ViewModule>): PanelView[] {
  return Object.values(modules)
    .map((module) => module.view)
    .toSorted((a, b) => a.order - b.order);
}

export const VIEWS: PanelView[] = sortViews(
  import.meta.glob<ViewModule>("./panels/*-view.tsx", { eager: true }),
);
