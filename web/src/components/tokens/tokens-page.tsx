import { useEffect, useState } from "react";

import type {
  AbPanel as AbData,
  ContextPanel as ContextData,
  EfficiencyPanel as EfficiencyData,
  LeversPanel as LeversData,
  OverviewPanel,
  SessionsPanel as SessionsData,
  TokensIndex,
} from "../../lib/tokens-types.ts";

import {
  fetchPanel,
  fetchTokensIndex,
  fromSearch,
  type TokenQuery,
  toSearch,
} from "../../lib/tokens-api.ts";
import { AbBanner, AbPanel } from "./ab-panel.tsx";
import { ContextFile, ContextPanel } from "./context-panel.tsx";
import { EfficiencyPanel } from "./efficiency-panel.tsx";
import { FilterBar } from "./filter-bar.tsx";
import { LeversPanel } from "./levers-panel.tsx";
import { SessionDetail } from "./session-detail.tsx";
import { SessionsPanel } from "./sessions-panel.tsx";
import { SpendPanel } from "./spend-panel.tsx";

interface Panels {
  ab: AbData;
  context: ContextData;
  efficiency: EfficiencyData;
  levers: LeversData;
  overview: OverviewPanel;
  sessions: SessionsData;
}

function useAsync<T>(load: (signal: AbortSignal) => Promise<T>, key: string) {
  const [state, setState] = useState<{ error: null | string; value: null | T }>({
    error: null,
    value: null,
  });
  useEffect(() => {
    const controller = new AbortController();
    const run = async (): Promise<void> => {
      try {
        const value = await load(controller.signal);
        setState({ error: null, value });
      } catch (error_: unknown) {
        if (!controller.signal.aborted) setState({ error: String(error_), value: null });
      }
    };
    void run();
    return () => {
      controller.abort();
    };
    // `load` is rebuilt every render; `key` is what identifies the request.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);
  return state;
}

async function loadPanels(query: TokenQuery, signal: AbortSignal): Promise<Panels> {
  const [overview, sessions, efficiency, levers, ab, context] = await Promise.all([
    fetchPanel<OverviewPanel>("overview", query, signal),
    fetchPanel<SessionsData>("sessions", query, signal),
    fetchPanel<EfficiencyData>("efficiency", query, signal),
    fetchPanel<LeversData>("levers", query, signal),
    fetchPanel<AbData>("ab", query, signal),
    fetchPanel<ContextData>("context", query, signal),
  ]);
  return { ab, context, efficiency, levers, overview, sessions };
}

function Coverage({ index }: Readonly<{ index: TokensIndex }>): React.JSX.Element {
  const { coverage } = index;
  const refreshed = new Date(coverage.refreshed_at * 1000);
  return (
    <p className="category">
      Full per-session detail from <strong>{coverage.detail_from ?? "—"}</strong> to{" "}
      {coverage.detail_to ?? "—"}; aggregate-only session totals (session-autopsy,
      main sessions, estimated USD) from {coverage.aggregate_from ?? "—"}; prompt
      counts from {coverage.any_from ?? "—"}. Store refreshed{" "}
      {refreshed.toLocaleString()}. List prices,
      deduplicated per API message; 0 LLM tokens.
    </p>
  );
}

export function TokensPage({
  route,
}: Readonly<{ route: { id: string; name: string } }>): React.JSX.Element {
  const hashQuery = globalThis.location.hash.split("?", 2)[1] ?? "";
  const [query, setQuery] = useState<TokenQuery>(() => fromSearch(hashQuery));
  const index = useAsync(fetchTokensIndex, "index");
  const panels = useAsync((signal) => loadPanels(query, signal), toSearch(query));
  const onChange = (next: TokenQuery): void => {
    setQuery(next);
    globalThis.history.replaceState(null, "", `#/tokens?${toSearch(next)}`);
  };
  const banner = index.value === null ? null : <AbBanner banner={index.value.ab_banner} />;
  if (route.name === "tokens-session") {
    return (
      <>
        {banner}
        <SessionDetail id={route.id} />
      </>
    );
  }
  if (route.name === "tokens-file") {
    return (
      <>
        {banner}
        <ContextFile data={panels.value?.context ?? null} path={route.id} />
      </>
    );
  }
  const error = index.error ?? panels.error;
  return (
    <>
      {banner}
      <h2 className="page-title">Claude Code spend</h2>
      {index.value !== null && <Coverage index={index.value} />}
      {index.value !== null && (
        <FilterBar index={index.value} onChange={onChange} query={query} />
      )}
      {error !== null && (
        <p className="empty" role="alert">
          {error}
        </p>
      )}
      {panels.value === null || index.value === null ? (
        error === null && <p className="empty">Reading…</p>
      ) : (
        <>
          <SpendPanel
            data={panels.value.overview}
            index={index.value}
            snapshotMetrics={index.value.snapshot_metrics}
          />
          <EfficiencyPanel data={panels.value.efficiency} />
          <AbPanel data={panels.value.ab} />
          <LeversPanel data={panels.value.levers} />
          <SessionsPanel data={panels.value.sessions} />
          <ContextPanel data={panels.value.context} />
        </>
      )}
    </>
  );
}
