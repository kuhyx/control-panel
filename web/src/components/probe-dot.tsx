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

export function ProbeDot({
  probe,
}: Readonly<{ probe: ProbeRecord }>): React.JSX.Element {
  const label = probeLabel(probe);
  return (
    <span
      aria-label={label}
      className="dot probe-dot"
      role="img"
      style={{ backgroundColor: probeTone(probe) }}
      title={label}
    />
  );
}
