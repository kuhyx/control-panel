import { afterEach, describe, expect, it, vi } from "vitest";

import {
  postedBodies,
  SESSIONS,
  stubSessionsFetch,
} from "../test/sessions-fixture.ts";
import {
  fetchSessions,
  markSession,
  resumeSession,
  sessionsFromSearch,
  sessionsToSearch,
  statusCounts,
  visibleSessions,
} from "./sessions-api.ts";

afterEach(() => {
  vi.unstubAllGlobals();
});

const ids = (query: { q: string; showDone: boolean }): string[] =>
  visibleSessions(SESSIONS.sessions, query).map((s) => s.id);

describe("sessions query", () => {
  it("defaults to done hidden and no filter", () => {
    expect(sessionsFromSearch("")).toEqual({ q: "", showDone: false });
    expect(sessionsToSearch({ q: "", showDone: false })).toBe("");
  });

  it("round-trips through the hash query", () => {
    const query = { q: "Fix router", showDone: true };
    const search = sessionsToSearch(query);
    expect(search).toBe("done=1&q=Fix+router");
    expect(sessionsFromSearch(search)).toEqual(query);
  });
});

describe("visibleSessions", () => {
  it("hides done rows unless asked, keeping the server order", () => {
    expect(ids({ q: "", showDone: false })).toEqual([
      "alpha",
      "bravo",
      "charlie",
      "delta",
    ]);
    expect(ids({ q: "", showDone: true })).toHaveLength(7);
  });

  it("matches project, title and cwd case-insensitively", () => {
    expect(ids({ q: "ROUTER", showDone: false })).toEqual(["charlie"]);
    expect(ids({ q: "delta-box", showDone: false })).toEqual(["delta"]);
    expect(ids({ q: "  bravo ", showDone: false })).toEqual(["bravo"]);
    expect(ids({ q: "golf", showDone: false })).toEqual([]);
    expect(ids({ q: "golf", showDone: true })).toEqual(["golf"]);
  });
});

describe("statusCounts", () => {
  it("counts every status over all rows, skipping empty ones", () => {
    expect(statusCounts(SESSIONS.sessions)).toBe(
      "1 need action · 1 question · 1 untagged · 1 running · 2 done · 1 continuing",
    );
    const two = [SESSIONS.sessions[1], SESSIONS.sessions[1]].filter(
      (s) => s !== undefined,
    );
    expect(statusCounts(two)).toBe("2 questions");
    expect(statusCounts([])).toBe("no sessions");
  });
});

describe("sessions endpoints", () => {
  it("reads the list", async () => {
    stubSessionsFetch();
    await expect(fetchSessions()).resolves.toEqual(SESSIONS);
  });

  it("posts the resume and mark bodies", async () => {
    const spy = stubSessionsFetch();
    await resumeSession("alpha");
    await markSession("alpha", "done");
    await markSession("alpha", null);
    expect(postedBodies(spy, "session-resume")).toEqual([{ id: "alpha" }]);
    expect(postedBodies(spy, "session-mark")).toEqual([
      { id: "alpha", mark: "done" },
      { id: "alpha", mark: null },
    ]);
  });
});
