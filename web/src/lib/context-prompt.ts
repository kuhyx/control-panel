// "Copy optimisation prompt": a ready-to-paste Claude prompt that asks for the
// chosen context files to be shrunk below their limits.
import type { ContextFileRow } from "./tokens-types.ts";

function limitText(row: ContextFileRow): string {
  return row.breaches.length === 0 ? [...row.hard_limits, ...row.budgets].join("; ") || "—" : row.breaches
    .map(
      (b) =>
        `${b.limit.toLocaleString("en-US")} ${b.measure} (${b.hard ? "hard" : "budget"}: ${b.why})`,
    )
    .join("; ");
}

// Default choice: every file that is over a hard limit or a budget.
export function overLimit(rows: ContextFileRow[]): ContextFileRow[] {
  return rows.filter((row) => row.status !== "ok");
}

export function optimisationPrompt(
  rows: ContextFileRow[],
  measureCommand: string,
): string {
  const table = rows.map((row) => {
    const cells = [
      row.path,
      row.bytes === null ? "gone" : String(row.bytes),
      row.lines === null ? "—" : String(row.lines),
      String(row.tokens),
      limitText(row),
      `$${row.usd_per_day.toFixed(4)}`,
    ];
    return `| ${cells.join(" | ")} |`;
  });
  const paths = rows.map((row) => row.path).join(" ");
  return [
    `Shrink these ${String(rows.length)} Claude Code context files below their limits.`,
    "",
    "| path | bytes | lines | tokens | limit | standing $/day |",
    "|---|---|---|---|---|---|",
    ...table,
    "",
    "For each file: shrink it below its limit without dropping any rule's prohibition, " +
      "command, path or memory entry. Move detail to on-demand files (read only when " +
      "needed) and link them, rather than deleting it.",
    `Verify every file afterwards with: ${measureCommand.split("{paths}").join(paths)}`,
    "Commit narrowly: only these files and the on-demand files you create.",
    "",
  ].join("\n");
}
