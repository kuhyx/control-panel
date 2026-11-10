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
} from "./sessions-api.ts";

afterEach(() => {
  vi.unstubAllGlobals();
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
