import type { SessionStatus } from "./sessions-api.ts";
import type { MarkFilter } from "./sessions-query.ts";
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

// Plain characters, not red emoji: the badge's own fill is red for the two
// that want kuhy, and a red glyph vanished on it.
export const SESSION_GLYPH: Record<SessionStatus, string> = {
  continuing: "↻",
  done: "✓",
  needs_action: "!",
  question: "?",
  running: "▶",
  untagged: "⬚",
};

// Session done-marks: by hand, by the session's own DONE tag, not done; `all`
// is the filter's no-filter option.
export const MARK_GLYPH: Record<MarkFilter, string> = {
  all: "∗",
  manual: "✋",
  open: "○",
  tag: "🏷",
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
  copy: "⧉",
  dashboards: "📊",
  delete: "🗑",
  error: "⚠",
  fail: "✕",
  findings: "✦",
  home: "⌂",
  logs: "📜",
  mark: "✔",
  none: "∅",
  notes: "📝",
  ok: "✓",
  probes: "📡",
  project: "📁",
  reading: "⟳",
  refused: "⊘",
  restart: "↻",
  resume: "▶",
  search: "🔍",
  sessions: "⌨",
  state: "🚦",
  stricter: "🔒",
  subsystem: "🧩",
  title: "💬",
  undo: "↶",
  units: "⚙",
  unknown: "🗃",
  usage: "📉",
  why: "💡",
} as const;
