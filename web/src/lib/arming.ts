import type { Arming, Level } from "./types.ts";

// Which token colours each state. Semantic fill only — never a categorical
// hue, which the design system reserves for charts and tags.
const TONE: Record<Arming, string> = {
  ARMED: "var(--success)",
  BAD: "var(--danger)",
  DEGRADED: "var(--warning)",
  NOT_INSTALLED: "var(--danger)",
  RETIRED: "var(--text-muted)",
  UNARMED: "var(--warning)",
  UNKNOWN: "var(--accent)",
};

// Worst first. Mirrors ARMING_SEVERITY in control_panel/_types.py; a subsystem
// reports the worst state among its units, and the table sorts the same way.
const SEVERITY: Arming[] = [
  "BAD",
  "NOT_INSTALLED",
  "UNARMED",
  "DEGRADED",
  "UNKNOWN",
  "RETIRED",
  "ARMED",
];

export function toneFor(state: Arming): string {
  return TONE[state];
}

export function severityRank(state: Arming): number {
  return SEVERITY.indexOf(state);
}

// RETIRED is a deliberate decision, not a fault, so it is not "needs attention".
export function requiresAttention(state: Arming): boolean {
  return state !== "ARMED" && state !== "RETIRED";
}

export function levelTone(level: Level): string {
  if (level === "danger") return "var(--danger)";
  if (level === "warn") return "var(--warning)";
  return "var(--accent)";
}
