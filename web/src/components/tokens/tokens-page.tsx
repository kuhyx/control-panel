import { useState } from "react";

import type {
  ContextPanel as ContextData,
  TokensIndex,
} from "../../lib/tokens-types.ts";

import {
  fetchPanel,
  fetchTokensIndex,
  fromSearch,
  type TokenQuery,
  toSearch,
} from "../../lib/tokens-api.ts";
import { useAsync } from "../../lib/use-async.ts";
import { AbBanner } from "./ab-panel.tsx";
import { ContextFile } from "./context-panel.tsx";
import { FilterBar } from "./filter-bar.tsx";
import { LazyPanel } from "./lazy-panel.tsx";
import { PageTabs } from "./page-tabs.tsx";
import { SessionDetail } from "./session-detail.tsx";
import { VIEWS } from "./views.ts";

function Coverage({
  index,
}: Readonly<{ index: TokensIndex }>): React.JSX.Element {
  const { coverage } = index;
  const refreshed = new Date(coverage.refreshed_at * 1000);
  return (
    <p className="category">
      Full per-session detail from{" "}
      <strong>{coverage.detail_from ?? "—"}</strong> to{" "}
      {coverage.detail_to ?? "—"}; aggregate-only session totals
      (session-autopsy, main sessions, estimated USD) from{" "}
      {coverage.aggregate_from ?? "—"}; prompt counts from{" "}
      {coverage.any_from ?? "—"}. Store refreshed {refreshed.toLocaleString()}.
      List prices, deduplicated per API message; 0 LLM tokens.
    </p>
  );
}

function ContextFileRoute({
  path,
  query,
}: Readonly<{ path: string; query: TokenQuery }>): React.JSX.Element {
  const context = useAsync(
    (signal) => fetchPanel<ContextData>("context", query, signal),
    "context-file",
  );
  return <ContextFile data={context.value} path={path} />;
}

const ROUTE_PREFIX: Record<string, string> = {
  "tokens-panel": "#/tokens/p/",
  "tokens-session": "#/tokens/s/",
};

// Where the query is written back (the file view has no tables to change).
function hashBase(route: { id: string; name: string }): string {
  const prefix = ROUTE_PREFIX[route.name];
  return prefix === undefined
    ? "#/tokens"
    : `${prefix}${encodeURIComponent(route.id)}`;
}

export function TokensPage({
  route,
}: Readonly<{ route: { id: string; name: string } }>): React.JSX.Element {
  const hashQuery = globalThis.location.hash.split("?", 2)[1] ?? "";
  const [query, setQuery] = useState<TokenQuery>(() => fromSearch(hashQuery));
  const index = useAsync(fetchTokensIndex, "index");
  const onChange = (next: TokenQuery): void => {
    setQuery(next);
    const search = toSearch(next);
    const suffix = search === "" ? "" : `?${search}`;
    globalThis.history.replaceState(null, "", hashBase(route) + suffix);
  };
  const loaded = index.value;
  const banner =
    index.value === null ? null : <AbBanner banner={index.value.ab_banner} />;
  if (route.name === "tokens-session") {
    return (
      <>
        {banner}
        <SessionDetail id={route.id} onQuery={onChange} query={query} />
      </>
    );
  }
  if (route.name === "tokens-file") {
    return (
      <>
        {banner}
        <ContextFileRoute path={route.id} query={query} />
      </>
    );
  }
  return (
    <>
      {banner}
      <PageTabs active="spend" />
      <h2 className="page-title">Claude Code spend</h2>
      {index.value !== null && <Coverage index={index.value} />}
      {index.value !== null && (
        <FilterBar index={index.value} onChange={onChange} query={query} />
      )}
      {index.error !== null && (
        <p className="empty" role="alert">
          {index.error}
        </p>
      )}
      {loaded === null
        ? index.error === null && <p className="empty">Reading…</p>
        : VIEWS.filter(
            (view) => route.name !== "tokens-panel" || view.name === route.id,
          ).map((view) => {
            return (
              <LazyPanel
                index={loaded}
                key={view.name}
                onQuery={onChange}
                query={query}
                view={view}
              />
            );
          })}
    </>
  );
}
