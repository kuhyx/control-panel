import { useEffect, useState } from "react";

import type { Rationale } from "../lib/types.ts";

import { fetchWhy } from "../lib/api.ts";
import { levelTone } from "../lib/arming.ts";
import { GLYPH } from "../lib/glyphs.ts";
import { ErrorNote } from "./error-note.tsx";
import { Glyph } from "./glyph.tsx";

// control_panel/_rationale.py's placeholder for an empty audit log: the
// server's sentence, not the log's content, so it is painted as "∅".
const NO_ENTRIES = "no entries recorded";

// Two sources, deliberately. The artifacts are what was already written down
// -- unit-file comments, incident write-ups, the reason columns of the two
// audit logs -- and they carry the panel on their own. The rules are the
// hand-written sidecar, for the rules whose reason was never recorded.
export function WhyPanel({ id }: Readonly<{ id: string }>): React.JSX.Element {
  const [why, setWhy] = useState<null | Rationale>(null);
  const [error, setError] = useState<null | string>(null);

  useEffect(() => {
    const controller = new AbortController();
    const read = async (): Promise<void> => {
      try {
        setWhy(await fetchWhy(id, controller.signal));
      } catch (error_: unknown) {
        if (!controller.signal.aborted) setError(String(error_));
      }
    };
    void read();
    return () => {
      controller.abort();
    };
  }, [id]);

  if (error !== null) return <ErrorNote error={error} />;
  if (!why) return <progress aria-label="Reading rationale…" />;
  if (why.rules.length === 0 && why.artifacts.length === 0) {
    // Not in a unit comment, a policy document, an audit log, or the sidecar.
    return (
      <p aria-label="No rationale is recorded" className="empty" role="status">
        {GLYPH.none}
      </p>
    );
  }

  // Signals are server sentences: a toned dot plus a level glyph, the
  // message spoken. Rules and artifacts are what someone wrote down: shown.
  return (
    <section aria-label="Why this is enforced">
      {why.signals.map((signal) => {
        return (
          <p aria-label={signal.message} className="empty" key={signal.code} role="note">
            <span
              className="dot"
              style={{ backgroundColor: levelTone(signal.level) }}
            />
            <span aria-hidden="true">{signal.level === "info" ? "ℹ" : GLYPH.error}</span>
          </p>
        );
      })}

      {why.rules.map((rule) => {
        return (
        <article className="rule" key={rule.id}>
          <h4>{rule.id}</h4>
          <p>{rule.why}</p>
          {rule.ratchet !== "" && (
            <p className="rule-field">
              <span aria-label="Ratchet" className="rule-label">⏳</span>
              {rule.ratchet}
            </p>
          )}
          {rule.cost_of_bypass !== "" && (
            <p className="rule-field">
              <span aria-label="Cost of bypass" className="rule-label">💸</span>
              {rule.cost_of_bypass}
            </p>
          )}
        </article>
        );
      })}

      {why.artifacts.map((artifact) => {
        return (
        <details className="artifact" key={`${artifact.kind}/${artifact.label}`}>
          <summary>
            {artifact.label}
            <span className="category">
              <Glyph glyph="📄" label={artifact.kind} />
            </span>
          </summary>
          {artifact.excerpt === NO_ENTRIES ? (
            <p aria-label={NO_ENTRIES} className="empty" role="status">
              {GLYPH.none}
            </p>
          ) : (
            <pre className="log">{artifact.excerpt}</pre>
          )}
        </details>
        );
      })}
    </section>
  );
}
