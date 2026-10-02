// Mirrors control_panel/_types.py exactly. `null` rather than `undefined`
// throughout, because these come straight from JSON, which has no undefined.

export type Arming =
  | "ARMED"
  | "BAD"
  | "DEGRADED"
  | "NOT_INSTALLED"
  | "RETIRED"
  | "UNARMED"
  | "UNKNOWN";

export type Level = "danger" | "info" | "warn";

export type Category = "enforcement" | "maintenance" | "server" | "telemetry";

export interface UnitState {
  active_state: null | string;
  exec_start: null | string;
  exec_start_exists: boolean | null;
  last_trigger: null | string;
  next_elapse: null | string;
  preset: null | string;
  result: null | string;
  sub_state: null | string;
  unit_file_state: null | string;
}

export interface UnitRecord {
  arming: Arming;
  arming_reason: string[];
  declared_retired: boolean;
  installed: boolean;
  login_oneshot: boolean;
  name: string;
  restartable: boolean;
  scope: "system" | "user";
  state: UnitState;
}

export interface ProbeRecord {
  detail: null | string;
  kind: string;
  latency_ms: null | number;
  status: null | number;
  target: string;
  // null: deliberately not probed (a public URL, or an on-demand UI).
  up: boolean | null;
}

export interface DashboardRecord {
  label: string;
  on_demand: boolean;
  probe: ProbeRecord;
  url: string;
}

export interface ContainerRecord {
  arming: Arming;
  name: string;
  restartable: boolean;
  state: string;
  status: string;
}

export interface LogReference {
  bytes: null | number;
  id: string;
  kind: string;
  mtime: null | string;
  path: null | string;
  rotated: boolean | null;
  scope: null | string;
  unit: null | string;
}

export interface Signal {
  code: string;
  level: Level;
  message: string;
}

export interface AdapterError {
  argv: string[];
  kind: string;
  message: string;
}

export interface SubsystemStatus {
  category: Category;
  containers: ContainerRecord[];
  dashboards: DashboardRecord[];
  facts: Record<string, unknown>;
  id: string;
  important: boolean;
  logs: LogReference[];
  probes: ProbeRecord[];
  read_at: string;
  reason: string;
  source: string;
  state: Arming;
  title: string;
  units: UnitRecord[];
}

export interface Anomaly {
  detail: string;
  evidence: string[];
  id: string;
  severity: Level;
  subsystem: string;
  title: string;
}

export interface Collector {
  degraded: boolean;
  duration_ms: number;
  journal_readable: boolean;
  warnings: string[];
}

export interface FleetStatus {
  anomalies: Anomaly[];
  collector: Collector;
  generated_at: string;
  host: string;
  port: number;
  rollup: Partial<Record<Arming, number>>;
  schema_version: number;
  subsystems: SubsystemStatus[];
}

export interface LogTail {
  error?: null | string;
  id: string;
  lines: string[];
  note?: string;
  path?: string;
  total_bytes: null | number;
  truncated: boolean;
}

export type JournalSource = "docker" | "system" | "user";

// What /api/journal/<source>/<name> answers, and what /api/logs/<id> answers
// for a journal-kind log.
export interface JournalTail {
  error: string;
  lines: string[];
  name: string;
  ok: boolean;
  source: JournalSource;
}

export interface Listener {
  address: string;
  port: number;
  process: string;
}

export interface UndeclaredUnit {
  name: string;
  scope: string;
}

export interface UnknownReport {
  listeners: Listener[];
  units: UndeclaredUnit[];
}

export interface Artifact {
  excerpt: string;
  kind: string;
  label: string;
  source: string;
}

export interface Rule {
  added: string;
  cost_of_bypass: string;
  id: string;
  ratchet: string;
  supersedes: string[];
  why: string;
}

export interface Rationale {
  artifacts: Artifact[];
  rules: Rule[];
  signals: Signal[];
  subsystem: string;
}

export interface MutationResult {
  argv: string[];
  ok: boolean;
  // Distinct from !ok: a refusal is the ratchet working and is rendered as
  // such, not as an error.
  refused: boolean;
  stderr: string;
  stdout: string;
  summary: string;
}
