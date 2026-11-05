# control-panel

A loopback-only dashboard for every enforcement subsystem, server, container
and timer on this machine — with a link to each one's own web UI, its logs, and
*why* each rule exists. It lives in the i3 bar as a tray icon.

```
./install.sh                            # build, run as a user service, add the tray
python -m control_panel doctor          # the arming table, no server
./run.sh --dashboards                   # probe every dashboard link; exit 1 on a dead one
python -m control_panel serve           # http://127.0.0.1:8760
```

## The tray icon

`scripts/control_panel_tray.py` (installed to `~/.config/i3/scripts`, started by
an `exec` line in the i3 config) is a 2x2 grid in the bar. **Left-click** opens
the panel. **Right-click** lists every subsystem with a coloured dot; each opens
a submenu of that subsystem's dashboards. The icon is **red** when an
`important` subsystem is BAD, NOT_INSTALLED or UNARMED, **amber** when anything
else is unhealthy, neutral when all is well, and grey when the panel does not
answer. The script decides none of that: it renders `GET /api/tray`, which is
computed and tested server-side.

## Servers, containers and dashboards

A manifest entry may declare `dashboards` (`{label, url, on_demand?}`),
`containers` (Docker, read with one `docker ps`), `probes` and `important`.
Loopback and tailnet URLs are probed concurrently every collection; public
`*.duckdns.org` URLs are links only, because probing them goes through the
router's flaky DNS. On a `server` subsystem a dead probe is BAD; elsewhere the
UI is a convenience and a dead one is DEGRADED. `GET /api/unknown` lists TCP
listeners and user unit files that **no** entry declares, so a server started
last week cannot hide.

## Why it exists

The digital-wellbeing and self-hosting fleet spans ~10 repos and ~29 systemd
timers, and its failure mode is silent: enforcement that has stopped firing
looks exactly like enforcement that never needed to fire. Two examples, both
found by this tool on its first run:

- **`phone-auto-sync.timer` was never installed here.** An installer in
  `~/src/phone-focus-mode` references it, but no unit file exists on this machine,
  so the phone policy has never been pushed.
- **`kuhytrack-budget.timer` is disabled** while its preset is `enabled` —
  kuhytrack has been tracking without ever enforcing.

Neither is discoverable by enumerating systemd, because the first one *is not in
systemd*. That single fact drives the design.

## How it works

**The fleet is declared, not discovered.** `manifest/subsystems/*.json` states
what should exist; systemd is compared against it. Three things live there
because they cannot be computed:

| Field | Why it must be declared |
|---|---|
| `retired` | systemd has no concept of one unit superseding another |
| `login_oneshot` | a `disabled` unit pulled in by a target is still armed |
| `snapshot_dirs` | an orphaned `disabled-*` folder is just a folder to systemd |

Everything else is computed. `control_panel/_arming.py` is a pure function with
no I/O, which is why its nine rules are exhaustively tested.

### Three findings that only showed up by running it

- **`TriggeredBy` is a runtime edge.** A *disabled* timer contributes nothing to
  it, so trusting it reported `kuhytrack-budget.service` as ARMED (`static`)
  while the timer that fires it was off. Delegation is built from declared
  timers' `Unit=` instead, which systemd reports regardless of enablement.
- **`list-unit-files` lists templates, not instances.** `guard-file@.path` is
  listed; `guard-file@hosts.path` and its three siblings are not — so all four
  live guard-lib guards read as NOT_INSTALLED until `systemctl show` is used as
  the fallback.
- **A timer can be enabled, tracked, and still never fire.**
  `pc-startup-monitor.timer` has no next elapse because systemd will not re-arm
  a timer whose `RemainAfterExit` oneshot is still active. It gets `DEGRADED`
  with that explanation rather than a bare `UNARMED`.

## Why a rule exists

`GET /api/why/<subsystem>` answers it from **two** sources, and the first one
carries the panel on its own:

**(a) What is already written down**, quoted rather than summarised —
unit-file comments, the security-hardening docs, incident write-ups, and the
free-text `reason` columns of `/etc/shutdown-schedule-overrides.conf` and
`exception_audit.log`. The comments are the surprise here: in this fleet the
reasoning sits *beside the directive it justifies*, several lines into a
section, so an extractor that stops at the first `[Unit]` header finds nothing.
`leetcode-guard.timer` explains its `Persistent=true` flip that way, and that
comment is now surfaced automatically.

**(b) `rationale/<subsystem>.json`**, hand-written, for the rules whose reason
was never recorded anywhere. It carries `why`, `cost_of_bypass`, `ratchet` and
`added`. Missing, malformed or partial sidecars degrade to a warning chip and
the artifacts still render — never an exception, never a blank panel.

The `ratchet` field earns its place immediately: `shutdown.morning-end-hour`
records that it ratchets **the opposite way** from the two evening hours, because
`day-specific-shutdown-check.sh:94` shuts down while the clock is *below* it, so
a larger value is a longer window and therefore stricter. Writing `-gt` there,
as the evening hours do, would ratchet it backwards — which is exactly the
mistake Phase 2 would otherwise make.

## Stricter only, and enforced as such

Most subsystems have no writable surface at all. The two enforcement ones that
do can only be tightened, and **this repo contains no comparator** — "is that
stricter?" is answered by the scripts that already guard those files, so the
dashboard is structurally incapable of permitting something they would refuse.

| Endpoint | Delegates to | Why it cannot loosen |
|---|---|---|
| `POST /api/mutate/shutdown-hours` | `screen-locker`'s `adjust_shutdown_schedule.sh`, **never with `--restore`** | the script rejects any value that is not stricter, and its stderr is relayed verbatim |
| `POST /api/mutate/hosts-add` | append, then `hosts-blocker/install.sh` | the installer aborts if any entry disappeared, so appending is the only edit that survives |
| `POST /api/mutate/restart` | `systemctl --user restart` / `docker restart` | allowlisted in the manifest, and the loader **refuses** `restartable` on anything but a user unit or container in a `server` subsystem. A restart leaves a unit exactly as armed as it was, so it cannot switch a guard off. |
| `POST /api/mutate/session-resume` | `systemd-run --user --collect … terminator -x zsh -lic 'claude --resume <id>'` | approved 2026-10-22. Not a guard: the id must be a canonical UUID of a scanned session, the cwd comes from its transcript, and the transient unit has no unit file to arm or disarm. Body `{id}` or `{ids}` (at most 5, all-or-nothing). |
| `POST /api/mutate/session-mark` | atomic write of `~/.claude/session-status.json` | approved 2026-10-22. The dashboard's own manual "done" marks for the Sessions tab; no guard reads them. Body `{id, mark}` or `{ids, mark}` (all-or-nothing). |
| `POST /api/mutate/session-delete` | rename of `~/.claude/projects/<dir>/<uuid>.jsonl` (+ its `<uuid>/` subagent dir) into `~/.claude/projects-trash/<YYYY-MM-DD>/<dir>/` | approved 2026-10-22. Never unlinks: restore is a move back. Refuses the whole request if any id is unknown, was written in the last 10 minutes (may be live), or resolves outside `~/.claude/projects`. |
| `GET /api/mutate/steam-exceptions` | nothing — view only | the enforcer loads `config.json` once and re-`chattr +i`s it every 3s tick, so a write here would be silently reverted. The panel says so instead of offering a dead control. |

Two pre-commit hooks state the boundary rather than leaving it to discipline.
`no-writes-outside-mutations` keeps every other module a reader.
`never-change-unit-state` applies **everywhere, mutations included**: nothing may
start, stop, enable, disable or mask a unit. Restart is the one allowed unit
operation, and `restart-only-in-restart-module` confines it to
`mutations/_restart.py`. Every POST must be `application/json` with a `Host` of
this listener, which stops cross-site forms and DNS rebinding. This tool reports that a timer is
unarmed and lets you go and arm it yourself — a button that runs `systemctl
enable` is how a monitoring tool quietly becomes a control plane.

Related deliberate choices:

- **Binds `127.0.0.1` only, and that is not configurable.** The payload names
  every enforcement mechanism, which ones are off, and where each policy file
  lives. There is no authentication, so the bind address is the entire access
  control. Verified unreachable over LAN, WireGuard and Tailscale.
- **The port guard refuses; it never reaps.** Unlike `~/src/todo`, which may reclaim
  its port because browser storage is origin-keyed, this holds no such state. It
  identifies the owner and exits. A test asserts no signal is ever sent.
- **Logs are read bounded.** `/var/log/hosts-file-monitor.log` is 57 MB; nothing
  reads more than the last 64 KiB, and the partial first line is discarded.
- **Steam's root-owned caches are reported `UNKNOWN`, not escalated to.** `kuhy`
  has `NOPASSWD: ALL`, so sudo would work — which is exactly why not doing it is
  the thing that keeps "read-only" true.

## Development

```bash
python -m venv .venv && .venv/bin/pip install -e .
.venv/bin/pytest                       # 573 tests, 100% branch coverage

pnpm --dir web install                 # pnpm only: npm cannot install
pnpm --dir web run lint                #   @kuhyx/web-ui from a git subdirectory
pnpm --dir web run coverage            # 241 tests, 100% branch coverage
pnpm --dir web run build               # -> web/dist, served by the Python process

pre-commit run --all-files
```

The frontend consumes `@kuhyx/web-ui` tokens and introduces **no colour
literals** — a pre-commit hook fails the commit if a hex appears, because the
palette is CI-compared across four files in `~/src/utils`.

Two test seams, and only two: `CONTROL_PANEL_ROOT` for the filesystem (required,
with no default, so a test that forgets it raises rather than reading the real
`/etc`) and a `CommandRunner` protocol for systemd.
