import type { TokensIndex } from "../../lib/tokens-types.ts";
import type { PanelView } from "./views.ts";

import {
  fetchPanel,
  panelSearch,
  type TokenQuery,
} from "../../lib/tokens-api.ts";
import { useAsync } from "../../lib/use-async.ts";
import { TableScope } from "./table-scope.tsx";

interface Answered {
  filters?: { since: number; until: number };
}

function unlimited(query: TokenQuery, key: string): TokenQuery {
  return { ...query, tables: { ...query.tables, [`t.${key}.limit`]: "0" } };
}

// Every matching row of one table of a panel (its limit lifted).
export async function loadAll(
  panel: string,
  query: TokenQuery,
  id: string,
): Promise<object[]> {
  const payload = await fetchPanel<Record<string, unknown>>(
    panel,
    unlimited(query, `${panel}/${id}`),
  );
  const rows = payload[id];
  return Array.isArray(rows) ? (rows as object[]) : [];
}

// One panel: fetches its own data under the page's filters and its own
// tables' parameters, and renders it inside its table scope, or a per-panel
// loading / error line.
export function LazyPanel({
  index,
  onQuery,
  query,
  view,
}: Readonly<{
  index: TokensIndex;
  onQuery: (next: TokenQuery) => void;
  query: TokenQuery;
  view: PanelView;
}>): React.JSX.Element {
  const state = useAsync(
    (signal) => fetchPanel<Answered>(view.name, query, signal),
    `${view.name}?${panelSearch(query, view.name)}`,
  );
  if (state.value !== null) {
    const scope = {
      loadAll: (id: string) => loadAll(view.name, query, id),
      onQuery,
      panel: view.name,
      query,
      title: view.title,
      window: state.value.filters ?? null,
    };
    return (
      <TableScope scope={scope}>
        {view.render(state.value, { index })}
      </TableScope>
    );
  }
  return (
    <section className="card" id={view.name}>
      {state.error === null ? (
        <p className="empty">Reading {view.title}…</p>
      ) : (
        <p className="empty" role="alert">
          {view.title}: {state.error}
        </p>
      )}
    </section>
  );
}
