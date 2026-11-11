import type { Arming, Category, JournalSource } from "./types.ts";

// kuhy's textgate rule: nothing he sees carries words he did not ask for.
// Every enum the UI used to print as a word maps to one glyph here, so a
// glyph means the same thing on every page. Each glyph rides with a second
// channel (the state tone, a count, a position) and the old word stays as the
// spoken-only aria-label.

// Shapes, not just colours: a check is fine, a cross is broken, an empty set
// is missing, a dashed ring is present but not armed, pause/stop are the two
// deliberate decisions.
export const ARMING_GLYPH: Record<Arming, string> = {
  ARMED: "✓",
  BAD: "✕",
  DEGRADED: "◐",
  DISARMED: "⏸",
  NOT_INSTALLED: "∅",
  RETIRED: "⏹",
  UNARMED: "◌",
  UNKNOWN: "?",
};

// Filter options arrive as plain strings; an unexpected one reads as UNKNOWN.
export function armingGlyph(value: string): string {
  return (ARMING_GLYPH as Readonly<Record<string, string>>)[value] ?? ARMING_GLYPH.UNKNOWN;
}

export function scopeGlyph(value: string): string {
  return (SCOPE_GLYPH as Readonly<Record<string, string>>)[value] ?? "•";
}

export const CATEGORY_GLYPH: Record<Category, string> = {
  enforcement: "🔒",
  maintenance: "🔧",
  // VS16 forces the colour emoji; bare U+1F5A5 renders as a thin text glyph.
  server: "🖥️",
  telemetry: "📈",
};

// Shell prompts: `#` is root (the system manager), `$` a user session.
export const SCOPE_GLYPH: Record<JournalSource, string> = {
  docker: "⬡",
  system: "#",
  user: "$",
};

// systemd UnitFileState values; anything else falls back to a bullet with the
// raw value spoken.
const UNIT_FILE_GLYPH: Readonly<Record<string, string>> = {
  disabled: "○",
  enabled: "●",
  generated: "⚙",
  indirect: "↪",
  linked: "🔗",
  masked: "⊗",
  static: "◆",
};

export function unitFileGlyph(state: string): string {
  return UNIT_FILE_GLYPH[state] ?? "•";
}

// Shared action and section glyphs, one job each.
export const GLYPH = {
  actions: "⚡",
  age: "⏱",
  clear: "✕",
  containers: "📦",
  dashboards: "📊",
  error: "⚠",
  fail: "✕",
  findings: "✦",
  home: "⌂",
  logs: "📜",
  none: "∅",
  notes: "📝",
  ok: "✓",
  probes: "📡",
  reading: "⟳",
  refused: "⊘",
  restart: "↻",
  sessions: "⌨",
  state: "🚦",
  stricter: "🔒",
  subsystem: "🧩",
  units: "⚙",
  usage: "📉",
  why: "💡",
} as const;
