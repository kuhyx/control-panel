import { useEffect, useState } from "react";

export interface Route {
  id: string;
  name:
    | "detail"
    | "logs"
    | "overview"
    | "tokens"
    | "tokens-file"
    | "tokens-panel"
    | "tokens-session"
    | "tokens-sessions";
}

const OVERVIEW: Route = { id: "", name: "overview" };
const SESSIONS: Route = { id: "", name: "tokens-sessions" };

// A hand-rolled hash router: a handful of routes do not justify a dependency,
// and a hash route needs no server-side rewrite rule on the Python static
// handler.
//
// A hash may carry a query -- `#/s/hosts?units.sort=state:desc` -- which holds
// table sort/filter/search state (see table-state.ts) or the token page's
// filters. It is not part of the route, so it is cut off before the path is
// read.
export function parseHash(hash: string): Route {
  const [path = ""] = hash.split("?", 1);
  const clean = path.replace(/^#\/?/, "");
  const [head = "", tail = "", rest = ""] = clean.split("/", 3);
  if (head === "tokens") {
    // Before the `rest === ""` check: `#/tokens/sessions` has no third part.
    if (tail === "sessions") return SESSIONS;
    if (rest === "") return { id: "", name: "tokens" };
    if (tail === "f") return { id: decodeURIComponent(rest), name: "tokens-file" };
    if (tail === "p") return { id: decodeURIComponent(rest), name: "tokens-panel" };
    return tail === "s"
      ? { id: decodeURIComponent(rest), name: "tokens-session" }
      : { id: "", name: "tokens" };
  }
  if (head === "s" && tail !== "") return { id: tail, name: "detail" };
  return head === "logs" && tail !== "" ? { id: tail, name: "logs" } : OVERVIEW;
}

// A loop rather than `/\/+$/`: that regex backtracks super-linearly.
function trimTrailingSlashes(path: string): string {
  let end = path.length;
  while (end > 0 && path[end - 1] === "/") end -= 1;
  return path.slice(0, end);
}

// `/tokens` (and `/tokens/sessions`) is a real path too (the server falls back to index.html for any
// unknown path), so a bookmark or `curl localhost:8760/tokens` lands on the
// token page; a hash, when present, still wins.
export function parseLocation(pathname: string, hash: string): Route {
  if (hash !== "" && hash !== "#" && hash !== "#/") return parseHash(hash);
  const path = trimTrailingSlashes(pathname);
  if (path === "/tokens/sessions") return SESSIONS;
  return path === "/tokens" ? { id: "", name: "tokens" } : parseHash(hash);
}

export function useRoute(): Route {
  const [route, setRoute] = useState<Route>(() =>
    parseLocation(globalThis.location.pathname, globalThis.location.hash),
  );
  useEffect(() => {
    const onChange = (): void => {
      setRoute(
        parseLocation(globalThis.location.pathname, globalThis.location.hash),
      );
    };
    globalThis.addEventListener("hashchange", onChange);
    return () => {
      globalThis.removeEventListener("hashchange", onChange);
    };
  }, []);
  return route;
}
