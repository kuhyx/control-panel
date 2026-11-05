// A small markdown renderer that only ever builds React elements: no HTML
// from the file is ever injected, so a context file cannot script the page.
// Covers what context files use: headings, paragraphs, lists, quotes, fenced
// code, tables, front matter, and inline code / bold / italic / links.
// Links keep only http(s), mailto and in-page targets; anything else is text.

import { Fragment } from "react";

const SAFE_LINK = /^(?:https?:|mailto:|#)/i;

interface Token {
  end: number;
  node: (key: string) => React.JSX.Element;
}

function wrapped(
  text: string,
  at: number,
  mark: string,
): null | { end: number; inner: string } {
  if (!text.startsWith(mark, at)) return null;
  const close = text.indexOf(mark, at + mark.length);
  if (close <= at + mark.length) return null;
  return {
    end: close + mark.length,
    inner: text.slice(at + mark.length, close),
  };
}

function link(text: string, at: number): null | Token {
  if (text[at] !== "[") return null;
  const middle = text.indexOf("]", at + 1);
  if (text[middle + 1] !== "(") return null;
  const close = text.indexOf(")", middle + 2);
  if (middle <= at + 1 || close <= middle + 2) return null;
  const label = text.slice(at + 1, middle);
  const href = text.slice(middle + 2, close);
  if (href.includes(" ") || !SAFE_LINK.test(href)) return null;
  return {
    end: close + 1,
    node: (key) => {
      return (
        <a href={href} key={key} rel="noreferrer noopener" target="_blank">
          {label}
        </a>
      );
    },
  };
}

// The inline mark starting at `at`, if any (code, bold, italic, safe link).
function token(text: string, at: number): null | Token {
  const code = wrapped(text, at, "`");
  if (code !== null)
    return {
      end: code.end,
      node: (key) => <code key={key}>{code.inner}</code>,
    };
  const bold = wrapped(text, at, "**");
  if (bold !== null)
    return {
      end: bold.end,
      node: (key) => <strong key={key}>{bold.inner}</strong>,
    };
  const italic = text[at + 1] === " " ? null : wrapped(text, at, "*");
  if (italic !== null)
    return {
      end: italic.end,
      node: (key) => <em key={key}>{italic.inner}</em>,
    };
  return link(text, at);
}

function inline(text: string, keyBase: string): React.JSX.Element[] {
  const out: React.JSX.Element[] = [];
  let plain = "";
  const flush = (): void => {
    if (plain !== "")
      out.push(
        <Fragment key={`${keyBase}-${String(out.length)}`}>{plain}</Fragment>,
      );
    plain = "";
  };
  let at = 0;
  while (at < text.length) {
    const found = token(text, at);
    if (found === null) {
      plain += text.charAt(at);
      at += 1;
    } else {
      flush();
      out.push(found.node(`${keyBase}-${String(out.length)}`));
      at = found.end;
    }
  }
  flush();
  return out;
}

interface Block {
  kind: "code" | "h" | "ol" | "p" | "quote" | "table" | "ul";
  // Heading depth (0 for every other kind).
  level: number;
  lines: string[];
}

const ITEM = /^\s*(?:[-*+]|\d+\.)\s+/;

function kindOf(line: string): Block["kind"] {
  if (/^#{1,6}\s/.test(line)) return "h";
  if (/^\s*\d+\.\s+/.test(line)) return "ol";
  if (/^\s*[-*+]\s+/.test(line)) return "ul";
  if (line.startsWith(">")) return "quote";
  return line.trimStart().startsWith("|") ? "table" : "p";
}

function frontMatter(lines: string[]): number {
  if (lines[0]?.trim() !== "---") return 0;
  const end = lines.indexOf("---", 1);
  return end === -1 ? 0 : end + 1;
}

function addLine(out: Block[], line: string): void {
  if (line.trim() === "") {
    out.push({ kind: "p", level: 0, lines: [] });
    return;
  }
  const kind = kindOf(line);
  const last = out.at(-1);
  if (kind === "h") {
    const level = line.length - line.replace(/^#+/, "").length;
    out.push({ kind, level, lines: [line.slice(level).trim()] });
  } else if (last?.kind === kind && last.lines.length > 0) {
    last.lines.push(line);
  } else {
    out.push({ kind, level: 0, lines: [line] });
  }
}

export function blocks(text: string): Block[] {
  const lines = text.split("\n");
  const out: Block[] = [];
  const skip = frontMatter(lines);
  if (skip > 0)
    out.push({ kind: "code", level: 0, lines: lines.slice(0, skip) });
  let fence: Block | null = null;
  for (const line of lines.slice(skip)) {
    const isFence = line.trimStart().startsWith("```");
    if (fence !== null) {
      if (isFence) fence = null;
      else fence.lines.push(line);
    } else if (isFence) {
      fence = { kind: "code", level: 0, lines: [] };
      out.push(fence);
    } else {
      addLine(out, line);
    }
  }
  return out.filter((b) => b.lines.length > 0);
}

function isSeparator(line: string): boolean {
  return line.includes("-") && line.replaceAll(/[\s:|-]/g, "") === "";
}

function cells(row: string): string[] {
  return row
    .trim()
    .replaceAll(/^\||\|$/g, "")
    .split("|")
    .map((c) => c.trim());
}

function renderBlock(block: Block, key: string): React.JSX.Element {
  switch (block.kind) {
    case "code": {
      return <pre key={key}>{block.lines.join("\n")}</pre>;
    }
    case "h": {
      const Tag = `h${String(Math.min(block.level + 2, 6))}` as "h3";
      return <Tag key={key}>{inline(block.lines.join(" "), key)}</Tag>;
    }
    case "ol":
    case "ul": {
      const List = block.kind;
      return (
        <List key={key}>
          {block.lines.map((line, index) => {
            const itemKey = `${key}-${String(index)}`;
            return (
              <li key={itemKey}>{inline(line.replace(ITEM, ""), itemKey)}</li>
            );
          })}
        </List>
      );
    }
    case "quote": {
      return (
        <blockquote key={key}>
          {inline(
            block.lines.map((l) => l.replace(/^>\s?/, "")).join(" "),
            key,
          )}
        </blockquote>
      );
    }
    case "table": {
      const rows = block.lines
        .filter((l) => !isSeparator(l))
        .map((l) => cells(l));
      return (
        <table className="table md-table" key={key}>
          <tbody>
            {rows.map((row, r) => {
              const rowKey = `${key}-${String(r)}`;
              return (
                <tr key={rowKey}>
                  {row.map((cell, c) => {
                    const cellKey = `${rowKey}-${String(c)}`;
                    return <td key={cellKey}>{inline(cell, cellKey)}</td>;
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      );
    }
    default: {
      return <p key={key}>{inline(block.lines.join(" "), key)}</p>;
    }
  }
}

export function Markdown({
  text,
}: Readonly<{ text: string }>): React.JSX.Element {
  return (
    <div className="markdown">
      {blocks(text).map((block, index) =>
        renderBlock(block, `b${String(index)}`),
      )}
    </div>
  );
}
