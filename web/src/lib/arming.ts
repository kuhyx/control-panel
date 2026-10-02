import type { Arming, Level } from "./types.ts";

// Which token colours each state. Semantic fill only — never a categorical
// hue, which the design system reserves for charts and tags.
const TONE: Record<Arming, string> = {
  ARMED: "var(--success)",
  BAD: "var(--danger)",
  DEGRADED: "var(--warning)",
  DISARMED: "var(--text-muted)",
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
  "DISARMED",
  "RETIRED",
  "ARMED",
];

export function toneFor(state: Arming): string {
  return TONE[state];
}

export function severityRank(state: Arming): number {
  return SEVERITY.indexOf(state);
}

// RETIRED and DISARMED are deliberate decisions, not faults, so neither is
// "needs attention".
const SETTLED = new Set<Arming>(["ARMED", "DISARMED", "RETIRED"]);

export function requiresAttention(state: Arming): boolean {
  return !SETTLED.has(state);
}

export function levelTone(level: Level): string {
  if (level === "danger") return "var(--danger)";
  return level === "warn" ? "var(--warning)" : "var(--accent)";
}
