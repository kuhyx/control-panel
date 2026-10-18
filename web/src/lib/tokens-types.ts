import type { TableMeta } from "../components/tokens/data-table.tsx";

// Per-table counts and column kinds the backend's table layer adds.
export type Tables = Record<string, TableMeta>;

// Mirrors control_panel/tokens/*.py payloads. `null` where JSON has nulls.

export interface TokenFilters {
  cwd: string;
  model: string;
  scope: "all" | "main" | "sub";
  since: number;
  until: number;
}

export interface Banner {
  level: "green" | "grey" | "red";
  text: string;
}

export interface TokensIndex {
  ab_banner: Banner;
  coverage: {
    aggregate_from: null | string;
    any_from: null | string;
    detail_from: null | string;
    detail_to: null | string;
    refreshed_at: number;
    snapshots: string[];
  };
  options: { cwds: string[]; models: string[] };
  panels: { name: string; title: string }[];
  snapshot_metrics: Record<string, Record<string, number>>;
  store: string;
}

export interface DailyRow {
  calls: number;
  day: string;
  home_share: null | number;
  opus_share: null | number;
  over_share: null | number;
  sub_share: null | number;
  usd: number;
  usd_per_call: null | number;
}

export interface OverviewPanel {
  _tables?: Tables;
  aggregate: { day: string; sessions: number; usd_est: number }[];
  daily: DailyRow[];
  filters: TokenFilters;
  prompts: { day: string; prompts: number }[];
  tiles: {
    active_h: number;
    calls: number;
    sessions: number;
    usd: number;
    usd_per_call: null | number;
    usd_per_day: number;
  };
  weekly: { calls: number; usd: number; week: string }[];
}

export interface SessionRow {
  active_s: number;
  calls: number;
  cwd: null | string;
  final_tag: null | string;
  first_ts: number;
  key: string;
  last_ts: number;
  models: Record<string, number>;
  prompts: number;
  subagents: number;
  title: string;
  usd: number;
  usd_main: number;
  // The spend of the active scope (main / sub / all): what the list ranks by.
  usd_scope?: number;
  usd_sub: number;
  wall_s: number;
}

export interface SessionsPanel {
  _tables?: Tables;
  limit: number;
  scope?: string;
  sessions: SessionRow[];
}

export interface SubagentRow {
  active_s: number;
  agent_type: string;
  calls: number;
  depth: number;
  description: string;
  key: string;
  model: string;
  usd: number;
  wall_s: number;
}

export interface ToolRow {
  calls: number;
  carry_usd: number;
  name: string;
  result_tokens: number;
  share: null | number;
  usd: number;
}

export interface PromptRow {
  active_s: number;
  calls: number;
  idx: number;
  subagents: SubagentRow[];
  text: string;
  tools: ToolRow[];
  ts: number;
  usd: number;
  usd_own: number;
  usd_sub: number;
  wall_s: number;
}

export interface SessionDetail {
  _tables?: Tables;
  prompts: PromptRow[];
  session: SessionRow;
  unattributed: SubagentRow[];
}

export type EfficiencyWeek = Record<string, null | number | string> & {
  week: string;
};

export interface EfficiencyPanel {
  _tables?: Tables;
  captions: Record<"commits" | "done" | "estimate", string>;
  commits: EfficiencyWeek[];
  done: EfficiencyWeek[];
  estimate: EfficiencyWeek[];
  filtered_by?: string;
}

export interface LeverRow {
  actual: null | number;
  baseline: null | number;
  date: null | string;
  detail: null | string;
  lever: string;
  lower_is_better: number;
  metric: string;
  outcome: null | string;
  predicted: null | number;
  source: string;
  status: "applied" | "not applied" | "proposed";
}

export interface MetricPoint {
  date: string;
  value: null | number;
}

export interface LeversPanel {
  _tables?: Tables;
  rolling_days: number;
  rows: LeverRow[];
  series: Record<string, { daily: MetricPoint[]; snapshots: MetricPoint[] }>;
}

export interface RateCi {
  high: number;
  k: number;
  low: number;
  rate: null | number;
}

export interface MeanCi {
  high: number;
  low: number;
  mean: number;
}

export interface AbArm {
  correction: RateCi;
  duration_s: MeanCi;
  error: RateCi;
  followup: RateCi;
  n: number;
  redo: RateCi;
  tags: Record<string, number>;
  usd: MeanCi;
}

// One A/B measure: display strings per arm and Sonnet − Opus difference.
export interface AbMetric {
  difference: string;
  measure: string;
  opus: string;
  sonnet: string;
}

export interface AbPanel {
  _tables?: Tables;
  arms: Partial<Record<"opus" | "sonnet", AbArm>>;
  banner: Banner;
  diffs?: Record<string, { diff: number; high: number; low: number }>;
  filtered_by?: string;
  metrics?: AbMetric[];
  unjoined?: number;
}

export type {
  Breach,
  ContextFileDetail,
  ContextFileRow,
  ContextPanel,
} from "./tokens-types-context.ts";
