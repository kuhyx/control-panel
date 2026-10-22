import { afterEach, describe, expect, it, vi } from "vitest";

import {
  postedBodies,
  SESSIONS,
  stubSessionsFetch,
} from "../test/sessions-fixture.ts";
import {
  deleteSession,
  deleteSessions,
  fetchSessions,
  markSessions,
  resumeSessions,
  statusCounts,
} from "./sessions-api.ts";

afterEach(() => {
  vi.unstubAllGlobals();
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

  it("posts the bulk bodies, and a single delete by id", async () => {
    const spy = stubSessionsFetch();
    await markSessions(["alpha", "bravo"], "done");
    await markSessions(["alpha"], null);
    await resumeSessions(["alpha", "bravo"]);
    await deleteSessions(["echo", "golf"]);
    await deleteSession("echo");
    expect(postedBodies(spy, "session-mark")).toEqual([
      { ids: ["alpha", "bravo"], mark: "done" },
      { ids: ["alpha"], mark: null },
    ]);
    expect(postedBodies(spy, "session-resume")).toEqual([
      { ids: ["alpha", "bravo"] },
    ]);
    expect(postedBodies(spy, "session-delete")).toEqual([
      { ids: ["echo", "golf"] },
      { id: "echo" },
    ]);
  });
});
