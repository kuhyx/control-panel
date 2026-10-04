## Commands

- run: `./run.sh` (serves the dashboard on 127.0.0.1:8760; live service, `--doctor` for a no-server check)
- test: `pytest -q`
- test-changed: `scripts/test_changed.sh`
- lint: `pre-commit run ruff --all-files`
- coverage: `python3 -m pytest -q --cov --cov-branch --cov-report=lcov`
- coverage-gaps: `coverage-gaps coverage.lcov`
