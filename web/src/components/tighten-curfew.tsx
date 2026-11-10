import { useState } from "react";

import type { MutationResult } from "../lib/types.ts";

import { mutate } from "../lib/api.ts";
import { GLYPH } from "../lib/glyphs.ts";
import { ErrorNote } from "./error-note.tsx";

// Weekdays as ISO numbers (Mon = 1): the evening hour fields are a moon over
// a day range, the morning end a sun.
const MON_WED = "🌙 1–3";
const THU_SUN = "🌙 4–7";
const MORNING = "☀";

function HourField({
  glyph,
  label,
  onChange,
  value,
}: Readonly<{
  glyph: string;
  label: string;
  onChange: (value: string) => void;
  value: string;
}>): React.JSX.Element {
  return (
    <label>
      <span aria-hidden="true">{glyph}</span>
      <input
        aria-label={label}
        max="23"
        min="0"
        onChange={(event) => {
          onChange(event.target.value);
        }}
        type="number"
        value={value}
      />
    </label>
  );
}

// The three hours are sent as-is. This component contains no comparison
// against the current schedule, deliberately: the ratchet lives in
// screen-locker's adjust_shutdown_schedule.sh, and a second opinion here could
// only ever disagree with the one that actually guards the file. Earlier
// evening hours and a later morning end are stricter; the script's answer is
// shown as the outcome glyph, its stderr verbatim.
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
      <div className="fields">
        <HourField glyph={MON_WED} label="Mon–Wed" onChange={setMonWed} value={monWed} />
        <HourField glyph={THU_SUN} label="Thu–Sun" onChange={setThuSun} value={thuSun} />
        <HourField
          glyph={MORNING}
          label="Morning end"
          onChange={setMorningEnd}
          value={morningEnd}
        />
      </div>

      {confirming ? (
        <p className="confirm">
          {MON_WED} {monWed}:00 · {THU_SUN} {thuSun}:00 · {MORNING} {morningEnd}:00
          <button
            aria-label="Yes, tighten it"
            className="danger"
            disabled={busy}
            onClick={() => void submit()}
            type="button"
          >
            {GLYPH.stricter}?
          </button>
          <button
            aria-label="Cancel"
            onClick={() => {
              setConfirming(false);
            }}
            type="button"
          >
            {GLYPH.clear}
          </button>
        </p>
      ) : (
        <button
          aria-label="Tighten curfew"
          disabled={busy}
          onClick={() => {
            setConfirming(true);
          }}
          type="button"
        >
          {GLYPH.stricter}
        </button>
      )}

      {error !== null && <ErrorNote error={error} />}
      {result !== null && <MutationOutcome result={result} />}
    </section>
  );
}

function outcomeTone(result: MutationResult): string {
  if (result.ok) return "var(--success)";
  return result.refused ? "var(--warning)" : "var(--danger)";
}

function outcomeGlyph(result: MutationResult): string {
  if (result.ok) return GLYPH.ok;
  return result.refused ? GLYPH.refused : GLYPH.fail;
}

// Dot tone plus glyph shape for the verdict; the server's summary sentence is
// spoken only. stderr is the script's own output, shown verbatim like a log.
export function MutationOutcome({
  result,
}: Readonly<{ result: MutationResult }>): React.JSX.Element {
  const tone = outcomeTone(result);
  return (
    <div aria-label={result.summary} className="outcome" role="status">
      <p>
        <span className="dot" style={{ backgroundColor: tone }} />
        <span aria-hidden="true">{outcomeGlyph(result)}</span>
      </p>
      {result.stderr !== "" && <pre className="log">{result.stderr}</pre>}
    </div>
  );
}
