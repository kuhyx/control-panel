import { useEffect, useState } from "react";

export interface Route {
  id: string;
  name: "detail" | "logs" | "overview";
}

// A hand-rolled hash router: four routes do not justify a dependency, and a
// hash route needs no server-side rewrite rule on the Python static handler.
//
// A hash may carry a query -- `#/s/hosts?units.sort=state:desc` -- which holds
// table sort/filter/search state (see table-state.ts). It is not part of the
// route, so it is cut off before the path is read.
export function parseHash(hash: string): Route {
  const [path = ""] = hash.split("?", 1);
  const clean = path.replace(/^#\/?/, "");
  const [head = "", tail = ""] = clean.split("/", 2);
  if (head === "s" && tail !== "") return { id: tail, name: "detail" };
  return head === "logs" && tail !== ""
    ? { id: tail, name: "logs" }
    : { id: "", name: "overview" };
}

export function useRoute(): Route {
  const [route, setRoute] = useState<Route>(() =>
    parseHash(globalThis.location.hash),
  );
  useEffect(() => {
    const onChange = (): void => {
      setRoute(parseHash(globalThis.location.hash));
    };
    globalThis.addEventListener("hashchange", onChange);
    return () => {
      globalThis.removeEventListener("hashchange", onChange);
    };
  }, []);
  return route;
}
