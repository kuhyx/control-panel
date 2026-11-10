const KIB = 1024;
// Iterated by value rather than by index: indexing under
// noUncheckedIndexedAccess forces a `?? "B"` fallback that can never be taken,
// which is an untestable branch rather than a safeguard.
const UNITS = ["B", "KB", "MB", "GB", "TB"] as const;

export function formatBytes(bytes: null | number): string {
  if (bytes === null) return "—";
  let value = bytes;
  let name: (typeof UNITS)[number] = "B";
  for (const candidate of UNITS) {
    name = candidate;
    if (value < KIB) break;
    value /= KIB;
  }
  return `${value.toFixed(name === "B" ? 0 : 1)} ${name}`;
}

// systemd reports timestamps in MICROseconds since the epoch, not millis.
// Dividing by the wrong factor puts every "next run" in 1970.
const MICROS_PER_MS = 1000;

export function formatEpochMicros(raw: null | string): string {
  if (raw === null || raw === "") return "—";
  const micros = Number(raw);
  return !Number.isFinite(micros) || micros <= 0 ? "—" : formatLocal(new Date(micros / MICROS_PER_MS));
}

// Digits only ("2026-11-10 21:57:47", local time): toLocaleString paints
// words such as "PM" or month names in some locales.
function formatLocal(when: Date): string {
  const pad = (value: number): string => String(value).padStart(2, "0");
  const day = `${String(when.getFullYear())}-${pad(when.getMonth() + 1)}-${pad(when.getDate())}`;
  return `${day} ${pad(when.getHours())}:${pad(when.getMinutes())}:${pad(when.getSeconds())}`;
}

export function formatTimestamp(iso: string): string {
  const parsed = new Date(iso);
  return Number.isNaN(parsed.getTime()) ? iso : formatLocal(parsed);
}

const MS_PER_SECOND = 1000;
const SECONDS_PER_MINUTE = 60;

// "12 s" / "3 min" (the age glyph next to it says "ago"). A clock running slightly behind the server's must not
// render a negative age, so the floor is zero.
export function formatAge(iso: string, nowMs: number): string {
  const parsed = new Date(iso);
  const then = parsed.getTime();
  if (Number.isNaN(then)) return "—";
  const seconds = Math.max(0, Math.round((nowMs - then) / MS_PER_SECOND));
  return seconds < SECONDS_PER_MINUTE
    ? `${String(seconds)} s`
    : `${String(Math.floor(seconds / SECONDS_PER_MINUTE))} min`;
}

// Coarser than formatAge, for things days or weeks old: "7 s",
// "3 min", "3 h", "12 d". Floored at zero for a clock running
// behind, like formatAge.
const STEPS: readonly (readonly [number, string])[] = [
  [60, "s"],
  [60, "min"],
  [24, "h"],
];

export function formatRelativeAge(iso: string, nowMs: number): string {
  const then = Date.parse(iso);
  if (Number.isNaN(then)) return "—";
  let value = Math.max(0, Math.floor((nowMs - then) / MS_PER_SECOND));
  for (const [size, unit] of STEPS) {
    if (value < size) return `${String(value)} ${unit}`;
    value = Math.floor(value / size);
  }
  return `${String(value)} d`;
}
