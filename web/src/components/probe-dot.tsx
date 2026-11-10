import type { ProbeRecord } from "../lib/types.ts";

// Three states, three tones. "Not probed" is a decision (a public URL, or a UI
// that only exists while someone runs it), so it is muted rather than amber.
export function probeTone(probe: ProbeRecord): string {
  if (probe.up === null) return "var(--text-muted)";
  return probe.up ? "var(--success)" : "var(--danger)";
}

export function probeLabel(probe: ProbeRecord): string {
  if (probe.up === null) return probe.detail ?? "not probed";
  if (!probe.up) return `down: ${probe.detail ?? "no answer"}`;
  const status = probe.status === null ? "open" : String(probe.status);
  const latency =
    probe.latency_ms === null ? "" : ` · ${String(probe.latency_ms)} ms`;
  return `up ${status}${latency}`;
}

// The painted part of a probe answer: HTTP status and latency, digits only
// ("200 · 1.5 ms"); empty when nothing answered.
export function probeNumbers(probe: ProbeRecord): string {
  const parts: string[] = [];
  if (probe.status !== null) parts.push(String(probe.status));
  if (probe.latency_ms !== null) parts.push(`${String(probe.latency_ms)} ms`);
  return parts.join(" · ");
}

// The sentence from probeLabel is the spoken name only: no title, which would
// paint it on hover.
export function ProbeDot({
  probe,
}: Readonly<{ probe: ProbeRecord }>): React.JSX.Element {
  return (
    <span
      aria-label={probeLabel(probe)}
      className="dot probe-dot"
      role="img"
      style={{ backgroundColor: probeTone(probe) }}
    />
  );
}
