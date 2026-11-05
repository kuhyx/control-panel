import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { blocks, Markdown } from "./markdown.tsx";

const DOC = [
  "---",
  "name: x",
  "---",
  "# Title",
  "Some **bold**, *soft* and `code` text,",
  "joined. [ok](https://a.example) [bad](javascript:alert(1)) [in](#top)",
  "",
  "- one",
  "* two",
  "1. first",
  "2. second",
  "> quoted",
  "> more",
  "| a | b |",
  "|---|---|",
  "| 1 | **2** |",
  "```",
  "<script>alert(1)</script>",
  "```",
  "<b>raw html stays text</b>",
  "```",
  "unclosed fence",
].join("\n");

describe("Markdown", () => {
  it("renders the common blocks and inline marks as elements", () => {
    const { container } = render(<Markdown text={DOC} />);
    expect(screen.getByRole("heading", { name: "Title" }).tagName).toBe("H3");
    expect(screen.getByText("bold").tagName).toBe("STRONG");
    expect(screen.getByText("soft").tagName).toBe("EM");
    expect(screen.getByText("code").tagName).toBe("CODE");
    expect(screen.getByRole("link", { name: "ok" })).toHaveAttribute(
      "rel",
      "noreferrer noopener",
    );
    expect(screen.getByRole("link", { name: "in" })).toHaveAttribute(
      "href",
      "#top",
    );
    expect(screen.queryByRole("link", { name: "bad" })).toBeNull();
    expect(
      screen.getByText(/\[bad\]\(javascript:alert\(1\)\)/),
    ).toBeInTheDocument();
    expect(container.querySelectorAll(":scope ul li")).toHaveLength(2);
    expect(container.querySelectorAll(":scope ol li")).toHaveLength(2);
    expect(screen.getByText("quoted more").tagName).toBe("BLOCKQUOTE");
    expect(container.querySelectorAll(":scope .md-table tr")).toHaveLength(2);
    expect(container.querySelector(":scope script")).toBeNull();
    expect(screen.getByText("<script>alert(1)</script>").tagName).toBe("PRE");
    expect(screen.getByText("<b>raw html stays text</b>").tagName).toBe("P");
    expect(screen.getByText(/name: x/).tagName).toBe("PRE");
    expect(screen.getByText("unclosed fence").tagName).toBe("PRE");
  });

  it("caps heading depth and leaves an unterminated front matter as text", () => {
    const parsed = blocks("---\nnot closed\n###### deep\n#\tx");
    expect(parsed.map((b) => b.kind)).toEqual(["p", "h", "h"]);
    render(<Markdown text="###### deep" />);
    expect(screen.getByRole("heading", { name: "deep" }).tagName).toBe("H6");
  });

  it("leaves unclosed or empty marks and broken links as plain text", () => {
    for (const odd of [
      "a `` b",
      "x `open",
      "** c",
      "a * d",
      "[x] e",
      "[](#a)",
      "[y](#b g",
      "[z]( h",
    ]) {
      const { unmount } = render(<Markdown text={odd} />);
      expect(screen.getByText(odd)).toBeInTheDocument();
      expect(screen.queryByRole("link")).toBeNull();
      unmount();
    }
  });
});
