import { useState } from "react";

import type { MutationResult } from "../lib/types.ts";

import { mutate } from "../lib/api.ts";

// The three hours are sent as-is. This component contains no comparison
// against the current schedule, deliberately: the ratchet lives in
// screen-locker's adjust_shutdown_schedule.sh, and a second opinion here could
// only ever disagree with the one that actually guards the file.
export function TightenCurfew(): React.JSX.Element {
  const [monWed, setMonWed] = useState("21");
  const [thuSun, setThuSun] = useState("21");
  const [morningEnd, setMorningEnd] = useState("5");
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<MutationResult | null>(null);
  const [error, setError] = useState<null | string>(null);

  const submit = async (): Promise<void> => {
    setBusy(true);
    setConfirming(false);
    try {
      setResult(
        await mutate("shutdown-hours", {
          mon_wed_hour: Number(monWed),
          morning_end_hour: Number(morningEnd),
          thu_sun_hour: Number(thuSun),
        }),
      );
      setError(null);
    } catch (error_: unknown) {
      setError(String(error_));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section aria-label="Tighten the curfew" className="mutate">
      <p className="reason">
        Only a stricter schedule is accepted, and this page does not decide
        which that is — the request goes to the same script the sick-day flow
        uses, and its answer is shown verbatim below. Earlier evening hours are
        stricter; a <em>later</em> morning end is stricter, because it lengthens
        the shutdown window.
      </p>

      <div className="fields">
        <label>
          Mon–Wed
          <input
            max="23"
            min="0"
            onChange={(event) => {
              setMonWed(event.target.value);
            }}
            type="number"
            value={monWed}
          />
        </label>
        <label>
          Thu–Sun
          <input
            max="23"
            min="0"
            onChange={(event) => {
              setThuSun(event.target.value);
            }}
            type="number"
            value={thuSun}
          />
        </label>
        <label>
          Morning end
          <input
            max="23"
            min="0"
            onChange={(event) => {
              setMorningEnd(event.target.value);
            }}
            type="number"
            value={morningEnd}
          />
        </label>
      </div>

      {confirming ? (
        <p className="confirm">
          Apply Mon–Wed {monWed}:00, Thu–Sun {thuSun}:00, morning end{" "}
          {morningEnd}:00? This is written to a guarded file and cannot be
          loosened again from here.
          <button disabled={busy} onClick={() => void submit()} type="button">
            Yes, tighten it
          </button>
          <button
            onClick={() => {
              setConfirming(false);
            }}
            type="button"
          >
            Cancel
          </button>
        </p>
      ) : (
        <button
          disabled={busy}
          onClick={() => {
            setConfirming(true);
          }}
          type="button"
        >
          Tighten curfew…
        </button>
      )}

      {error !== null && <p className="empty" role="alert">{error}</p>}
      {result !== null && <MutationOutcome result={result} />}
    </section>
  );
}

// Three outcomes, three tones. A refusal is the guard doing its job, so it
// must not look like the danger red of a broken pipeline.
function outcomeTone(result: MutationResult): string {
  if (result.ok) return "var(--success)";
  return result.refused ? "var(--warning)" : "var(--danger)";
}

export function MutationOutcome({
  result,
}: Readonly<{ result: MutationResult }>): React.JSX.Element {
  const tone = outcomeTone(result);
  return (
    <div className="outcome" role="status">
      <p>
        <span className="dot" style={{ backgroundColor: tone }} />
        {result.summary}
      </p>
      {result.stderr !== "" && (
        <>
          <p className="category">what the script said</p>
          <pre className="log">{result.stderr}</pre>
        </>
      )}
    </div>
  );
}
