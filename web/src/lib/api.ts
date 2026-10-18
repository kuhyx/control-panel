import type {
  FleetStatus,
  JournalSource,
  JournalTail,
  LogTail,
  MutationResult,
  Rationale,
  UnknownReport,
} from "./types.ts";

export class ApiError extends Error {
  override readonly name = "ApiError";
}

export async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(path, signal ? { signal } : {});
  if (!response.ok) {
    throw new ApiError(`${path} responded ${String(response.status)}`);
  }
  try {
    return (await response.json()) as T;
  } catch {
    throw new ApiError(`${path} returned malformed JSON`);
  }
}

export function fetchStatus(signal?: AbortSignal): Promise<FleetStatus> {
  return getJson<FleetStatus>("/api/status", signal);
}

export function fetchLog(
  id: string,
  lines: number,
  signal?: AbortSignal,
): Promise<JournalTail | LogTail> {
  return getJson<JournalTail | LogTail>(
    `/api/logs/${encodeURIComponent(id)}?lines=${String(lines)}`,
    signal,
  );
}

export function fetchJournal(
  source: JournalSource,
  name: string,
  lines: number,
  signal?: AbortSignal,
): Promise<JournalTail> {
  return getJson<JournalTail>(
    `/api/journal/${source}/${encodeURIComponent(name)}?lines=${String(lines)}`,
    signal,
  );
}

export function fetchUnknown(signal?: AbortSignal): Promise<UnknownReport> {
  return getJson<UnknownReport>("/api/unknown", signal);
}

export function restart(
  kind: "container" | "unit",
  name: string,
): Promise<MutationResult> {
  return mutate("restart", { kind, name });
}

export function fetchWhy(id: string, signal?: AbortSignal): Promise<Rationale> {
  return getJson<Rationale>(`/api/why/${encodeURIComponent(id)}`, signal);
}

export async function mutate(
  name: string,
  body: unknown,
): Promise<MutationResult> {
  const response = await fetch(`/api/mutate/${encodeURIComponent(name)}`, {
    body: JSON.stringify(body),
    headers: { "Content-Type": "application/json" },
    method: "POST",
  });
  if (!response.ok) {
    throw new ApiError(`mutation ${name} responded ${String(response.status)}`);
  }
  try {
    return (await response.json()) as MutationResult;
  } catch {
    throw new ApiError(`mutation ${name} returned malformed JSON`);
  }
}
