import { useEffect, useState } from "react";

import { formatAge, formatTimestamp } from "../lib/format.ts";
import { GLYPH } from "../lib/glyphs.ts";
import { Glyph } from "./glyph.tsx";

const TICK_MS = 1000;

// The server serves a snapshot its background collector refreshes every 10 s,
// so the age is worth showing. The one-second tick lives here rather than in
// App so that it re-renders this text only, not the tables below it.
export function Freshness({
  at,
}: Readonly<{ at: string }>): React.JSX.Element {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const timer = setInterval(() => {
      setNow(Date.now());
    }, TICK_MS);
    return () => {
      clearInterval(timer);
    };
  }, []);
  return (
    <span title={formatTimestamp(at)}>
      <Glyph glyph={GLYPH.reading} label="updated" /> {formatAge(at, now)}
    </span>
  );
}
