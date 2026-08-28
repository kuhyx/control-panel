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
  if (!Number.isFinite(micros) || micros <= 0) return "—";
  const when = new Date(micros / MICROS_PER_MS);
  return when.toLocaleString();
}

export function formatTimestamp(iso: string): string {
  const parsed = new Date(iso);
  return Number.isNaN(parsed.getTime()) ? iso : parsed.toLocaleString();
}
