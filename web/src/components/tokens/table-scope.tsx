import { createContext, use, useState } from "react";

import type { TokenQuery } from "../../lib/tokens-api.ts";

import {
  EMPTY_TABLE,
  readTable,
  type TableState,
  writeTable,
} from "../../lib/table-parameters.ts";

// Where a table lives: its panel (the hash prefix of its state), the page's
// query and the window the panel answered for (for the copied header).
export interface Scope {
  onQuery: (next: TokenQuery) => void;
  panel: string;
  query: TokenQuery;
  title: string;
  window: null | { since: number; until: number };
}

const ScopeContext = createContext<null | Scope>(null);

export function TableScope({
  children,
  scope,
}: Readonly<{ children: React.ReactNode; scope: Scope }>): React.JSX.Element {
  return <ScopeContext value={scope}>{children}</ScopeContext>;
}

export function useScope(): null | Scope {
  return use(ScopeContext);
}

// A table's state: in the URL hash when inside a scope, else local.
export function useTableState(
  id: string,
): [TableState, (next: TableState) => void] {
  const scope = useScope();
  const [local, setLocal] = useState<TableState>(EMPTY_TABLE);
  if (scope === null) return [local, setLocal];
  const key = `${scope.panel}/${id}`;
  const set = (next: TableState): void => {
    scope.onQuery({
      ...scope.query,
      tables: writeTable(scope.query.tables, key, next),
    });
  };
  return [readTable(scope.query.tables, key), set];
}
