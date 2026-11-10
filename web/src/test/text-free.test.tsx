import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { JournalTail, Rationale, UnknownReport } from "../lib/types.ts";

import { App } from "../app.tsx";
import { BlockDomain } from "../components/block-domain.tsx";
import { TightenCurfew } from "../components/tighten-curfew.tsx";
import * as api from "../lib/api.ts";
import { STATUS } from "./fixture.ts";
import { SESSIONS, stubSessionsFetch } from "./sessions-fixture.ts";

// kuhy's textgate rule, as a test: nothing painted on any page may hold a
// 2+-letter word unless that word is CONTENT (a name, title, path or session
// text from the data). Chrome words (labels, enum states, server sentences)
// fail it. Spoken-only text (aria-label, .sr-only) is allowed; title and
// placeholder attributes are painted (hover, empty field), so they count.

const WORD = /[^\W\d_]{2,}/gu;
// Unit symbols next to a number are not words.
const UNITS = new Set(["GB", "KB", "MB", "min", "ms", "TB"]);
const CONTENT_KEYS = new Set([
  "address", "cwd", "excerpt", "facts", "host", "id", "label", "last_assistant",
  "last_user", "lines", "name", "path", "process", "project", "subsystem",
  "target", "title", "unit", "url", "why",
]);
// Server-built sentences and enum words: chrome even under a content parent.
const CHROME_KEYS = new Set([
  "anomalies", "arming_reason", "category", "detail", "evidence", "kind", "message",
  "reason", "signals", "state", "status", "warnings",
]);

const UNKNOWN: UnknownReport = {
  listeners: [
    { address: "0.0.0.0", port: 5353, process: "" },
    { address: "127.0.0.1", port: 9000, process: "ollama" },
  ],
  units: [{ name: "stray.service", scope: "user" }],
};

const JOURNAL: JournalTail = {
  error: "",
  lines: ["Nov 10 21:00 archlinux systemd[1]: Started."],
  name: "signal-bot.service",
  ok: false,
  source: "user",
};

const WHY: Rationale = {
  artifacts: [
    {
      excerpt: "Persistent=true on purpose.",
      kind: "unit-comment",
      label: "dns-blocklist-refresh.timer",
      source: "systemctl cat",
    },
  ],
  rules: [
    {
      added: "2026-03-01",
      cost_of_bypass: "",
      id: "hosts.add-only",
      ratchet: "",
      supersedes: [],
      why: "Blocked domains stay blocked.",
    },
  ],
  signals: [{ code: "no-sidecar", level: "warn", message: "no sidecar rule" }],
  subsystem: "hosts",
};

function collect(node: unknown, isContent: boolean, into: Set<string>): void {
  if (Array.isArray(node)) {
    for (const item of node) collect(item, isContent, into);
  } else if (node !== null && typeof node === "object") {
    for (const [key, value] of Object.entries(node)) {
      if (!CHROME_KEYS.has(key)) collect(value, isContent || CONTENT_KEYS.has(key), into);
    }
  } else if (typeof node === "string" && isContent && node.trim().length > 1) {
    into.add(node.trim());
  }
}

const CONTENT: string[] = (() => {
  const found = new Set<string>();
  for (const source of [STATUS, SESSIONS, UNKNOWN, WHY, JOURNAL]) collect(source, false, found);
  // A finding's sentence is chrome; the subsystem id it links to is content.
  collect(STATUS.anomalies.map((a) => a.subsystem), true, found);
  return [...found].toSorted((a, b) => b.length - a.length);
})();

function isHidden(element: Element | null): boolean {
  for (let at = element; at !== null; at = at.parentElement) {
    if (["SCRIPT", "STYLE"].includes(at.tagName) || at.classList.contains("sr-only")) return true;
  }
  return false;
}

function paintedStrings(): string[] {
  const out: string[] = [];
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  for (let node = walker.nextNode(); node !== null; node = walker.nextNode()) {
    const text = node.textContent?.trim() ?? "";
    if (text !== "" && !isHidden(node.parentElement)) out.push(text);
  }
  for (const element of document.body.querySelectorAll("[title],[placeholder]")) {
    if (isHidden(element)) continue;
    for (const attribute of ["title", "placeholder"]) {
      const value = element.getAttribute(attribute);
      if (value !== null && value !== "") out.push(value);
    }
  }
  return out;
}

// A painted string is content when it is one content value, or a multi-word
// piece of one (markdown splits a reply into several text nodes). Otherwise
// every content value inside it is cut out and what is left must be wordless.
function chromeWords(text: string): string[] {
  if (CONTENT.some((value) => value === text || (text.includes(" ") && value.includes(text)))) {
    return [];
  }
  let rest = text;
  for (const value of CONTENT) rest = rest.replaceAll(value, " ");
  return (rest.match(WORD) ?? []).filter((word) => !UNITS.has(word));
}

function offenders(): string[] {
  const strings = paintedStrings();
  // An empty page is not text-free, it is broken.
  return strings.length === 0 ? ["<nothing rendered>"] : strings
    .map((text) => [chromeWords(text).join(" "), text] as const)
    .filter(([words]) => words !== "")
    .map(([words, text]) => `${words}  <-  ${text}`);
}

function goto(hash: string): void {
  globalThis.location.hash = hash;
  globalThis.dispatchEvent(new HashChangeEvent("hashchange"));
}

describe("text-free UI", () => {
  beforeEach(() => {
    globalThis.location.hash = "";
    vi.spyOn(api, "fetchStatus").mockResolvedValue(STATUS);
    vi.spyOn(api, "fetchUnknown").mockResolvedValue(UNKNOWN);
    vi.spyOn(api, "fetchWhy").mockResolvedValue(WHY);
    vi.spyOn(api, "fetchJournal").mockResolvedValue(JOURNAL);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("paints no chrome words on the fleet overview", async () => {
    render(<App />);
    expect(offenders()).toEqual([]);
    await screen.findByRole("table", { name: "Every declared subsystem" });
    await screen.findByRole("heading", { name: "Listening ports" });
    expect(offenders()).toEqual([]);
  });

  it.each(STATUS.subsystems.map((s) => s.id))(
    "paints no chrome words on the %s detail page, logs open",
    async (id) => {
      render(<App />);
      goto(`#/s/${id}`);
      await waitFor(() => {
        expect(screen.getByRole("heading", { level: 2 })).toBeInTheDocument();
      });
      await screen.findByRole("region", { name: "Why this is enforced" });
      const logButtons = screen.queryAllByRole("button", { name: /^Show logs/u });
      for (const button of logButtons) fireEvent.click(button);
      const restartButtons = screen.queryAllByRole("button", { name: /^Restart/u });
      for (const button of restartButtons) fireEvent.click(button);
      await waitFor(() => {
        expect(screen.queryAllByRole("status", { name: /^Reading/u })).toEqual([]);
      });
      expect(offenders()).toEqual([]);
    },
  );

  it("paints no chrome words on the sessions page, with a row open and selected", async () => {
    stubSessionsFetch();
    render(<App />);
    goto("#/sessions");
    const title = await screen.findByRole("button", { name: "title of alpha" });
    fireEvent.click(title);
    fireEvent.click(screen.getByRole("checkbox", { name: "Select alpha" }));
    fireEvent.click(screen.getByRole("button", { name: "Delete alpha" }));
    expect(offenders()).toEqual([]);
    // The empty state too: a filter that hides every row.
    fireEvent.change(screen.getByRole("searchbox", { name: "Filter sessions" }), {
      target: { value: "nothing-matches" },
    });
    expect(screen.getByRole("cell", { name: "No sessions match." })).toBeInTheDocument();
    expect(offenders()).toEqual([]);
    vi.unstubAllGlobals();
  });

  it("paints no chrome words on the two tighten-only forms, armed", () => {
    render(
      <>
        <TightenCurfew />
        <BlockDomain />
      </>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Tighten curfew" }));
    fireEvent.change(screen.getByRole("textbox", { name: "Domain" }), {
      target: { value: "example.org" },
    });
    expect(offenders()).toEqual([]);
  });
});
