import { describe, expect, it } from "vitest";

import { INDEX } from "../../test/tokens-fixture.ts";
import { sortViews, VIEWS } from "./views.ts";

describe("views", () => {
  it("orders self-registered views by their order", () => {
    const render = (): React.JSX.Element => <p />;
    const sorted = sortViews({
      "./panels/a-view.tsx": {
        view: { name: "a", order: 20, render, title: "A" },
      },
      "./panels/b-view.tsx": {
        view: { name: "b", order: 10, render, title: "B" },
      },
    });
    expect(sorted.map((v) => v.name)).toEqual(["b", "a"]);
    expect(sorted[0]?.render(null, { index: INDEX })).toEqual(<p />);
  });

  it("exposes the discovered views in order", () => {
    const orders = VIEWS.map((v) => v.order);
    expect(orders).toEqual(orders.toSorted((a, b) => a - b));
  });
});
