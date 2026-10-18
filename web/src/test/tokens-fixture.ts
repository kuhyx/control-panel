import type {
  AbArm,
  AbPanel,
  EfficiencyPanel,
  LeversPanel,
  OverviewPanel,
  SessionRow,
  SessionsPanel,
  TokensIndex,
} from "../lib/tokens-types.ts";

// Token-dashboard payloads shaped like control_panel/tokens/*.py output, with
// every nullable field exercised both ways somewhere.
export const INDEX: TokensIndex = {
  ab_banner: { level: "green", text: "Sonnet arm within tolerance" },
  coverage: {
    aggregate_from: "2026-01-01",
    any_from: null,
    detail_from: "2026-09-01",
    detail_to: null,
    refreshed_at: 1_760_000_000,
    snapshots: ["2026-10-01-window", "2026-10-08-window"],
  },
  options: { cwds: ["/home/kuhy/src/a", "/srv/b"], models: ["claude-opus"] },
  panels: [{ name: "overview", title: "Overview" }],
  snapshot_metrics: {
    "2026-10-01-window": { opus_usd_share: 0.4, usd_per_call: 0.05 },
  },
  store: "/home/kuhy/.local/share/control-panel/tokens.sqlite",
};

export const OVERVIEW: OverviewPanel = {
  aggregate: [{ day: "2026-08-30", sessions: 3, usd_est: 12 }],
  daily: [
    {
      calls: 1200,
      day: "2026-09-01",
      home_share: null,
      opus_share: 0.5,
      over_share: null,
      sub_share: 0.2,
      usd: 140,
      usd_per_call: 0.1,
    },
    {
      calls: 300,
      day: "2026-09-02",
      home_share: 0.1,
      opus_share: null,
      over_share: 0.3,
      sub_share: 0.1,
      usd: 30,
      usd_per_call: null,
    },
  ],
  filters: { cwd: "", model: "", scope: "all", since: 0, until: 0 },
  prompts: [{ day: "2026-09-01", prompts: 40 }],
  tiles: {
    active_h: 2.5,
    calls: 1500,
    sessions: 7,
    usd: 170,
    usd_per_call: null,
    usd_per_day: 85,
  },
  weekly: [{ calls: 1500, usd: 170, week: "2026-W36" }],
};

export const SESSION_ROW: SessionRow = {
  active_s: 4000,
  calls: 90,
  cwd: "/home/kuhy/src/a",
  final_tag: "DONE",
  first_ts: 1_760_000_000,
  key: "sess-1",
  last_ts: 1_760_004_000,
  models: { "claude-opus": 5, "claude-sonnet": 9 },
  prompts: 4,
  subagents: 2,
  title: "Fix the thing",
  usd: 12.5,
  usd_main: 10,
  usd_sub: 2.5,
  wall_s: 5000,
};

export const SESSIONS: SessionsPanel = {
  limit: 50,
  sessions: [
    SESSION_ROW,
    {
      ...SESSION_ROW,
      cwd: null,
      final_tag: null,
      key: "sess-2",
      models: {},
      title: "",
    },
  ],
};

export const EFFICIENCY: EfficiencyPanel = {
  captions: {
    commits: "Commits caption.",
    done: "Done caption.",
    estimate: "Est caption.",
  },
  commits: [
    {
      lost: 1,
      pending: "n/a",
      survived: 3,
      usd_per_survivor: 4,
      week: "2026-W36",
    },
  ],
  done: [
    { done_share: 0.5, untagged: 2, usd_per_done: 3, week: "2026-W36" },
    { done_share: null, untagged: null, usd_per_done: null, week: "2026-W37" },
  ],
  estimate: [{ usd_per_unit: 0.02, week: "2026-W36" }],
};

const LEVER = {
  actual: 0.3,
  baseline: 0.5,
  date: "2026-09-02",
  detail: "cut the rules",
  lever: "trim CLAUDE.md",
  lower_is_better: 1,
  metric: "usd_per_call",
  outcome: "better",
  predicted: 0.4,
  source: "ledger",
  status: "applied",
} as const;

export const LEVERS: LeversPanel = {
  rolling_days: 7,
  rows: [
    LEVER,
    {
      ...LEVER,
      baseline: null,
      date: null,
      detail: null,
      lever: "share lever",
      metric: "opus_usd_share",
      outcome: null,
      predicted: null,
    },
    { ...LEVER, lever: "count lever", metric: "calls_per_day" },
    {
      ...LEVER,
      lever: "idea",
      metric: "x",
      source: "proposals",
      status: "proposed",
    },
  ],
  series: {
    calls_per_day: {
      daily: [{ date: "2026-09-01", value: 2500 }],
      snapshots: [],
    },
    usd_per_call: {
      daily: [
        { date: "2026-09-01", value: 2 },
        { date: "2026-09-02", value: null },
      ],
      snapshots: [{ date: "2026-09-03", value: 0.5 }],
    },
  },
};

const ARM: AbArm = {
  correction: { high: 0.2, k: 1, low: 0.01, rate: 0.1 },
  duration_s: { high: 100, low: 20, mean: 60 },
  error: { high: 0.2, k: 0, low: 0, rate: null },
  followup: { high: 0.3, k: 2, low: 0.05, rate: 0.2 },
  n: 12,
  redo: { high: 0.1, k: 0, low: 0, rate: 0 },
  tags: { DONE: 3, RUNNING: 1 },
  usd: { high: 2, low: 0.5, mean: 1 },
};

export const AB: AbPanel = {
  arms: { sonnet: ARM },
  banner: { level: "grey", text: "too few" },
  diffs: { redo: { diff: -0.05, high: 0.1, low: -0.2 } },
  unjoined: 3,
};

export { CONTEXT, FILE } from "./context-fixture.ts";
