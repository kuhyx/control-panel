import { describe, expect, it } from "vitest";

import { NOW_MS, SESSIONS } from "../test/sessions-fixture.ts";
import {
  DEFAULT_QUERY,
  filterSessions,
  markOf,
  projectsOf,
  sessionsFromSearch,
  type SessionsQuery,
  sessionsToSearch,
  sortSessions,
} from "./sessions-query.ts";

const ids = (query: Partial<SessionsQuery>): string[] => {
  return filterSessions(SESSIONS.sessions, { ...DEFAULT_QUERY, ...query }, NOW_MS).map(
    (s) => s.id,
  );
};

const sorted = (column: string, direction: "asc" | "desc"): string[] =>
  sortSessions(SESSIONS.sessions, { column, direction }).map((s) => s.id);

describe("sessions hash query", () => {
  it("defaults to done hidden, no filter and server order", () => {
    expect(sessionsFromSearch("")).toEqual(DEFAULT_QUERY);
    expect(sessionsToSearch(DEFAULT_QUERY)).toBe("");
  });

  it("round-trips every key, done and q first as before", () => {
    const query: SessionsQuery = {
      ageN: "3",
      ageUnit: "w",
      mark: "manual",
      project: "panel",
      q: "Fix router",
      showDone: true,
      sort: { column: "age", direction: "desc" },
      statuses: ["needs_action", "done"],
    };
    const search = sessionsToSearch(query);
    expect(search).toBe(
      "done=1&q=Fix+router&status=needs_action&status=done&project=panel&older=3w&mark=manual&sort=age%3Adesc",
    );
    expect(sessionsFromSearch(search)).toEqual(query);
  });

  it("drops what it cannot read instead of guessing", () => {
    expect(
      sessionsFromSearch(
        "status=bogus&status=question&mark=nope&sort=cwd:asc&older=3y",
      ),
    ).toEqual({ ...DEFAULT_QUERY, statuses: ["question"] });
    expect(sessionsFromSearch("sort=title:sideways").sort).toBeNull();
    expect(sessionsFromSearch("older=1.5h")).toMatchObject({
      ageN: "1.5",
      ageUnit: "h",
    });
  });

  it("keeps an age only while its number is valid", () => {
    expect(sessionsToSearch({ ...DEFAULT_QUERY, ageN: "", ageUnit: "w" })).toBe("");
    expect(sessionsToSearch({ ...DEFAULT_QUERY, ageN: "-2" })).toBe("");
    expect(sessionsToSearch({ ...DEFAULT_QUERY, ageN: " 2 " })).toBe("older=2d");
  });
});

describe("filterSessions", () => {
  it("hides done rows unless asked, keeping the server order", () => {
    expect(ids({})).toEqual(["alpha", "bravo", "charlie", "delta"]);
    expect(ids({ showDone: true })).toHaveLength(7);
  });

  it("matches project, title and cwd case-insensitively", () => {
    expect(ids({ q: "ROUTER" })).toEqual(["charlie"]);
    expect(ids({ q: "delta-box" })).toEqual(["delta"]);
    expect(ids({ q: "  bravo " })).toEqual(["bravo"]);
    expect(ids({ q: "golf" })).toEqual([]);
    expect(ids({ q: "golf", showDone: true })).toEqual(["golf"]);
  });

  it("filters by status; ticking a done status shows those rows anyway", () => {
    expect(ids({ statuses: ["question", "running"] })).toEqual(["bravo", "delta"]);
    expect(ids({ statuses: ["done"] })).toEqual(["echo", "foxtrot"]);
    expect(ids({ statuses: ["continuing", "untagged"] })).toEqual([
      "charlie",
      "golf",
    ]);
  });

  it("filters by project", () => {
    expect(ids({ project: "panel" })).toEqual(["alpha", "bravo"]);
    expect(ids({ project: "panel", showDone: true })).toEqual([
      "alpha",
      "bravo",
      "echo",
    ]);
  });

  it("filters by how the row became done; done marks show themselves", () => {
    expect(ids({ mark: "manual" })).toEqual(["foxtrot"]);
    expect(ids({ mark: "tag" })).toEqual(["echo", "golf"]);
    expect(ids({ mark: "open", showDone: true })).toEqual([
      "alpha",
      "bravo",
      "charlie",
      "delta",
    ]);
  });

  it("keeps only rows older than N hours, days or weeks", () => {
    expect(ids({ ageN: "2", ageUnit: "h" })).toEqual(["alpha", "charlie"]);
    expect(ids({ ageN: "1", ageUnit: "d", showDone: true })).toEqual([
      "charlie",
      "echo",
      "foxtrot",
    ]);
    expect(ids({ ageN: "2", ageUnit: "w", showDone: true })).toEqual(["foxtrot"]);
    expect(ids({ ageN: "abc", ageUnit: "w" })).toHaveLength(4);
  });

  it("combines every filter with AND", () => {
    expect(
      ids({ ageN: "1", ageUnit: "d", mark: "tag", project: "panel" }),
    ).toEqual(["echo"]);
    expect(ids({ project: "panel", q: "bravo", statuses: ["question"] })).toEqual([
      "bravo",
    ]);
    expect(ids({ project: "router", statuses: ["question"] })).toEqual([]);
  });
});

describe("sortSessions", () => {
  it("sorts status by the server's priority order", () => {
    const shuffled = sortSessions(SESSIONS.sessions, {
      column: "title",
      direction: "desc",
    });
    expect(
      sortSessions(shuffled, { column: "status", direction: "asc" }).map(
        (s) => s.status,
      ),
    ).toEqual(["needs_action", "question", "untagged", "running", "done", "done", "continuing"]);
    expect(sorted("status", "desc")[0]).toBe("golf");
  });

  it("sorts age youngest first when ascending", () => {
    expect(sorted("age", "asc")).toEqual([
      "delta",
      "bravo",
      "golf",
      "alpha",
      "charlie",
      "echo",
      "foxtrot",
    ]);
    expect(sorted("age", "desc")[0]).toBe("foxtrot");
  });

  it("sorts project and title case-insensitively, ties in server order", () => {
    expect(sorted("project", "asc")).toEqual([
      "delta",
      "foxtrot",
      "golf",
      "alpha",
      "bravo",
      "echo",
      "charlie",
    ]);
    expect(sorted("title", "asc")[0]).toBe("charlie");
    expect(sorted("title", "desc")[0]).toBe("golf");
  });

  it("sorts mark by hand, then by tag, then not done", () => {
    expect(sorted("mark", "asc")).toEqual([
      "foxtrot",
      "echo",
      "golf",
      "alpha",
      "bravo",
      "charlie",
      "delta",
    ]);
  });

  it("leaves the server order alone when off or on an unknown column", () => {
    expect(sortSessions(SESSIONS.sessions, null)).toEqual(SESSIONS.sessions);
    expect(sorted("cwd", "desc")[0]).toBe("alpha");
  });
});

describe("helpers", () => {
  it("names each row's mark", () => {
    expect(SESSIONS.sessions.map((s) => markOf(s))).toEqual([
      "open",
      "open",
      "open",
      "open",
      "tag",
      "manual",
      "tag",
    ]);
  });

  it("lists distinct projects, sorted", () => {
    expect(projectsOf(SESSIONS.sessions)).toEqual([
      "delta",
      "foxtrot",
      "golf",
      "panel",
      "router",
    ]);
  });
});
