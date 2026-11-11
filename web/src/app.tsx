import { useEffect, useState } from "react";

import type { FleetStatus } from "./lib/types.ts";

import { AnomalyBanner } from "./components/anomaly-banner.tsx";
import { ErrorNote } from "./components/error-note.tsx";
import { FleetTable } from "./components/fleet-table.tsx";
import { Freshness } from "./components/freshness.tsx";
import { LogViewer } from "./components/log-viewer.tsx";
import { RollupTiles } from "./components/rollup-tiles.tsx";
import { SubsystemDetail } from "./components/subsystem-detail.tsx";
import { UnknownSection } from "./components/unknown-section.tsx";
import { UsageRedirect } from "./components/usage-redirect.tsx";
import { fetchStatus } from "./lib/api.ts";
import { formatTimestamp } from "./lib/format.ts";
import { GLYPH } from "./lib/glyphs.ts";
import { useRoute } from "./lib/router.ts";
import { SESSIONS_URL, USAGE_URL } from "./lib/usage-url.ts";

// Poll rather than stream: the server is a plain do_GET-only ThreadingHTTPServer
// with no SSE, and a 5s refresh is far finer than anything in this fleet moves.
const POLL_MS = 5000;

export function App(): React.JSX.Element {
  const [status, setStatus] = useState<FleetStatus | null>(null);
  const [error, setError] = useState<null | string>(null);
  const route = useRoute();

  useEffect(() => {
    const controller = new AbortController();
    // Defined inside the effect rather than hoisted into a useCallback: the
    // await means no setState happens synchronously, but the hooks lint can
    // only see that when the async function is local to the effect.
    const load = async (): Promise<void> => {
      try {
        const next = await fetchStatus(controller.signal);
        setStatus(next);
        setError(null);
      } catch (error_: unknown) {
        // An abort is this component unmounting, not a fault worth showing.
        if (!controller.signal.aborted) setError(String(error_));
      }
    };
    void load();
    const timer = setInterval(() => {
      void load();
    }, POLL_MS);
    return () => {
      controller.abort();
      clearInterval(timer);
    };
  }, []);

  return (
    <main>
      <header className="masthead">
        {/* The app's proper noun stays, spoken only; the nav glyphs are the
            visible masthead. */}
        <h1 className="sr-only">control-panel</h1>
        <nav className="masthead-nav">
          <a aria-label="fleet" href="#/">
            <span aria-hidden="true">{GLYPH.home}</span>
          </a>
          <a aria-label="Sessions" href={SESSIONS_URL}>
            <span aria-hidden="true">{GLYPH.sessions}</span>
          </a>
          <a aria-label="Usage" href={USAGE_URL}>
            <span aria-hidden="true">{GLYPH.usage}</span>
          </a>
        </nav>
        {status !== null && (
          <p className="category">
            {status.host} · {formatTimestamp(status.generated_at)} ·{" "}
            {status.collector.duration_ms} ms · <Freshness at={status.collected_at} />
          </p>
        )}
      </header>

      <Page error={error} route={route} status={status} />
    </main>
  );
}

function Page({
  error,
  route,
  status,
}: Readonly<{
  error: null | string;
  route: ReturnType<typeof useRoute>;
  status: FleetStatus | null;
}>): React.JSX.Element {
  return route.name === "usage" ? (
    <UsageRedirect />
  ) : (
    <Fleet error={error} route={route} status={status} />
  );
}

function Fleet({
  error,
  route,
  status,
}: Readonly<{
  error: null | string;
  route: ReturnType<typeof useRoute>;
  status: FleetStatus | null;
}>): React.JSX.Element {
  return (
    <>
      {error !== null && <ErrorNote error={error} />}
      {status === null && error === null && (
        <p aria-label="Reading" className="empty" role="status">
          {GLYPH.reading}
        </p>
      )}

      {status !== null && <Body route={route} status={status} />}
    </>
  );
}

function Body({
  route,
  status,
}: Readonly<{
  route: ReturnType<typeof useRoute>;
  status: FleetStatus;
}>): React.JSX.Element {
  if (route.name === "logs") return <LogViewer id={route.id} />;
  if (route.name === "detail") {
    const found = status.subsystems.find((s) => s.id === route.id);
    return found === undefined ? (
      <p aria-label="No such subsystem" className="empty" role="status">
        {GLYPH.none} <code>{route.id}</code>
      </p>
    ) : (
      <SubsystemDetail subsystem={found} />
    );
  }
  return (
    <>
      <RollupTiles rollup={status.rollup} />
      {/* Services first: the table is how you reach every dashboard, and a
          long findings list above it pushed it off the first screen. */}
      <FleetTable subsystems={status.subsystems} />
      <UnknownSection />
      <AnomalyBanner anomalies={status.anomalies} />
    </>
  );
}
