# control-panel

A loopback-only, **read-only** dashboard for every enforcement subsystem, server
and timer on this machine — and for *why* each rule exists.

```
python -m control_panel doctor          # the arming table, no server
python -m control_panel serve           # http://127.0.0.1:8770
```

## Why it exists

The digital-wellbeing and self-hosting fleet spans ~10 repos and ~29 systemd
timers, and its failure mode is silent: enforcement that has stopped firing
looks exactly like enforcement that never needed to fire. Two examples, both
found by this tool on its first run:

- **`phone-auto-sync.timer` was never installed here.** An installer in
  `~/phone-focus-mode` references it, but no unit file exists on this machine,
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

Eleven of the thirteen subsystems have no writable surface at all. The two that
do can only be tightened, and **this repo contains no comparator** — "is that
stricter?" is answered by the scripts that already guard those files, so the
dashboard is structurally incapable of permitting something they would refuse.

| Endpoint | Delegates to | Why it cannot loosen |
|---|---|---|
| `POST /api/mutate/shutdown-hours` | `screen-locker`'s `adjust_shutdown_schedule.sh`, **never with `--restore`** | the script rejects any value that is not stricter, and its stderr is relayed verbatim |
| `POST /api/mutate/hosts-add` | append, then `hosts-blocker/install.sh` | the installer aborts if any entry disappeared, so appending is the only edit that survives |
| `GET /api/mutate/steam-exceptions` | nothing — view only | the enforcer loads `config.json` once and re-`chattr +i`s it every 3s tick, so a write here would be silently reverted. The panel says so instead of offering a dead control. |

Two pre-commit hooks state the boundary rather than leaving it to discipline.
`no-writes-outside-mutations` keeps every other module a reader.
`never-change-unit-state` applies **everywhere, mutations included**: nothing may
start, stop, enable, disable or mask a unit. This tool reports that a timer is
unarmed and lets you go and arm it yourself — a button that runs `systemctl
enable` is how a monitoring tool quietly becomes a control plane.

Related deliberate choices:

- **Binds `127.0.0.1` only, and that is not configurable.** The payload names
  every enforcement mechanism, which ones are off, and where each policy file
  lives. There is no authentication, so the bind address is the entire access
  control. Verified unreachable over LAN, WireGuard and Tailscale.
- **The port guard refuses; it never reaps.** Unlike `~/todo`, which may reclaim
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
.venv/bin/pytest                       # 272 tests, 100% branch coverage

corepack pnpm --dir web install        # pnpm only: npm cannot install
corepack pnpm --dir web run lint       #   @kuhyx/web-ui from a git subdirectory
corepack pnpm --dir web run coverage   # 78 tests, 100% branch coverage
corepack pnpm --dir web run build      # -> web/dist, served by the Python process

pre-commit run --all-files
```

The frontend consumes `@kuhyx/web-ui` tokens and introduces **no colour
literals** — a pre-commit hook fails the commit if a hex appears, because the
palette is CI-compared across four files in `~/utils`.

Two test seams, and only two: `CONTROL_PANEL_ROOT` for the filesystem (required,
with no default, so a test that forgets it raises rather than reading the real
`/etc`) and a `CommandRunner` protocol for systemd.
