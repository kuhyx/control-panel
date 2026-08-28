import { useEffect, useState } from "react";

import type { Rationale } from "../lib/types.ts";

import { fetchWhy } from "../lib/api.ts";
import { levelTone } from "../lib/arming.ts";

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

  if (error !== null) return <p className="empty">{error}</p>;
  if (why === null) return <p className="empty">Reading rationale…</p>;
  if (why.rules.length === 0 && why.artifacts.length === 0) {
    return (
      <p className="empty">
        No rationale is recorded for this subsystem — not in a unit comment, a
        policy document, an audit log, or the sidecar.
      </p>
    );
  }

  return (
    <section aria-label="Why this is enforced">
      {why.signals.map((signal) => {
        return (
        <p className="empty" key={signal.code}>
          <span
            className="dot"
            style={{ backgroundColor: levelTone(signal.level) }}
          />
          {signal.message}
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
              <span className="rule-label">Ratchet</span>
              {rule.ratchet}
            </p>
          )}
          {rule.cost_of_bypass !== "" && (
            <p className="rule-field">
              <span className="rule-label">Cost of bypass</span>
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
            <span className="category">{artifact.kind}</span>
          </summary>
          <pre className="log">{artifact.excerpt}</pre>
        </details>
        );
      })}
    </section>
  );
}
