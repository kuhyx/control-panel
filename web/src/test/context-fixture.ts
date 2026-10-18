import type { ContextFileDetail, ContextPanel } from "../lib/tokens-types.ts";

export const CONTEXT: ContextPanel = {
  calls_per_day: 812.4,
  files: [
    {
      breaches: [
        {
          hard: true,
          limit: 200,
          measure: "lines",
          value: 300,
          why: "only 200 lines load",
        },
        {
          hard: false,
          limit: 250,
          measure: "lines",
          value: 300,
          why: "250-line cap",
        },
      ],
      budgets: ["250 lines"],
      bytes: 4000,
      hard_limits: ["200 lines"],
      history: [
        { bytes: 3000, source: "git", ts: 1_759_000_000 },
        { bytes: 4000, source: "disk", ts: 1_760_000_000 },
      ],
      kind: "global",
      lines: 300,
      path: "/home/kuhy/.claude/CLAUDE.md",
      standing: "always",
      status: "over hard limit",
      tokens: 1000,
      usd_per_day: 0.25,
      warning: "over 40k",
    },
    {
      breaches: [],
      budgets: [],
      bytes: null,
      hard_limits: [],
      history: [],
      kind: "repo",
      lines: null,
      path: "/srv/b/CLAUDE.md",
      standing: "repo",
      status: "ok",
      tokens: 0,
      usd_per_day: 0,
      warning: null,
    },
  ],
  measure_command: "wc -lc {paths}",
  price_per_mtok: 0.3,
};

export const FILE: ContextFileDetail = {
  content: "# rules",
  git_log: ["abc123 trim rules"],
  kind: "global",
  path: "/home/kuhy/.claude/CLAUDE.md",
};
