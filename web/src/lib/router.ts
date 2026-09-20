import { useEffect, useState } from "react";

export interface Route {
  id: string;
  name: "detail" | "logs" | "overview";
}

// A hand-rolled hash router: four routes do not justify a dependency, and a
// hash route needs no server-side rewrite rule on the Python static handler.
export function parseHash(hash: string): Route {
  const clean = hash.replace(/^#\/?/, "");
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
