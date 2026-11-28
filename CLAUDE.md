## Commands

- run: `./run.sh` (serves the dashboard on 127.0.0.1:8760; live service, `--doctor` for a no-server check)
- test: `pytest -q`
- test-changed: `scripts/test_changed.sh`
- lint: n/a: dropped (kuhy, 2026-11-27)
- coverage: n/a: dropped (kuhy, 2026-11-27)
- coverage-gaps: n/a: dropped (kuhy, 2026-11-27)
- deploy: `git -C ~/src/control-panel pull --ff-only && ~/src/control-panel/install.sh` (updates the live checkout, rebuilds web/dist, restarts control-panel-web, exits 1 unless /api/health answers)
