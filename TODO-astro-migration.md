# Migrate control-panel/web to Astro (no React)

## what
Rebuild the loopback dashboard (`web/`) as Astro 7 static pages. A `<script>`
on each page does the fetching and rendering in vanilla TS, and stateful
widgets become custom elements. `python -m control_panel serve` keeps serving
`web/dist` on 127.0.0.1:8760.

**Order: this repo migrates LAST, after every other repo.**

## steps
1. Do `~/src/utils/web_ui/TODO-astro-port.md` first. Then bump `@kuhyx/web-ui`
   from `web_ui-v0.3.2` to the new tag. `tokens.css` goes in the layout.
2. Pages. The `lib/router.ts` hash routes become two pages:
   - `src/pages/index.astro`: overview. `#/s/<id>` and `#/logs/<id>` stay as
     in-page hash views.
   - `src/pages/tokens/index.astro`: tokens, `#/f/`, `#/p/`, `#/s/` and `#/sessions`.
   A tiny script on `/` redirects old `#/tokens/...` links to `/tokens/#...`.
3. Server. `control_panel/_web_server.py` must try `<path>/index.html` before
   its SPA fallback. Add a test next to `tests/test_web_server.py`.
4. Rewrite the 102 React files by directory:
   - `components/*` (21): fleet, unit, container and probe tables, badges,
     log viewer, why/journal panels, restart and curfew buttons. Static parts
     become `.astro`. The buttons and the log viewer become custom elements.
   - `components/sessions/*` (8, plus hooks `use-poll`, `use-selection`):
     `<sessions-table>` custom element. The poll and selection become plain TS
     classes in `lib/`.
   - `components/tokens/*` (24), `tokens/groups/*` (25), `tokens/panels/*` (23):
     one generic `<data-table>` custom element replaces `data-table`,
     `table-head`, `table-toolbar`, `table-filters`, `table-scope` and
     `filter-bar` (sort, filter, CSV, copy). Panels become `.astro` shells
     plus TS renderers.
   - Charts (`line-chart`, `column-chart`, `chart-frame`, `spend-more-heatmap`)
     become SVG builders in `src/lib/charts/*.ts`.
   - `app.tsx` and `main.tsx` are deleted. `lib/use-async.ts` and the
     `useEffect` part of `router.ts` become plain functions.
5. Coverage. Keep the logic in `src/lib/**/*.ts` and `src/elements/**/*.ts`,
   and gate those at the current thresholds. `.astro` holds markup and one
   `import` per `<script>`.
6. Dependencies, from `web/`, exact pins via pnpm:
   - Add `astro@7.4.4`, `@astrojs/check@0.9.12`, `eslint-plugin-astro@3.2.1`
     and `@testing-library/dom`.
   - Remove `react`, `react-dom`, `@vitejs/plugin-react`,
     `@testing-library/react` and `eslint-plugin-react-hooks`.
   - Drop direct `vite` (Astro brings `^8.3.5`).
7. Tests. Use vitest 5.0.5 with `getViteConfig()`. Element tests go in jsdom
   with `@testing-library/dom` and `user-event`. Port the fixtures in
   `src/test/*` unchanged. Add one Container API test per page shell.
8. `build` becomes `astro check && astro build`, output `web/dist`.
   `run.sh --rebuild` stays as it is.
9. There is no `[agent_ready]` table. It is a loopback admin tool, so skip
   AgentReady.

## done
Run from `web/`:
`pnpm install --frozen-lockfile && pnpm lint && pnpm coverage && pnpm build`
Then:
`! grep -q '"react"' package.json && ! grep -qE '"(react-dom|@vitejs/plugin-react)"' package.json && ! find src -name '*.tsx' | grep -q .`
Both exit 0. Also from the repo root: `python -m pytest -q control_panel/tests/test_web_server.py`.

## verify
Run `systemctl --user restart control-panel-web.service`. Then:
- `curl -s http://127.0.0.1:8760/tokens/ | grep -q '<h1'`
- Use a headless chromium at 4K and at mobile size. The overview fleet table
  sorts, a restart button arms, the tokens panels load, and there are no
  console errors.

## read first
- `~/src/utils/web_ui/TODO-astro-port.md` (do it first)
- `web/src/lib/router.ts`, `web/src/components/tokens/data-table.tsx`, `web/src/app.tsx`
- `control_panel/_web_server.py`, `systemd/control-panel-web.service`, `run.sh`
- `README.md` (design tokens section)

REMOVE ME AFTER FINISH
