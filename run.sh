#!/bin/bash

# ============================================================================
# Build the frontend if needed, then serve the dashboard on loopback.
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR
readonly PORT="${CONTROL_PANEL_PORT:-8760}"

usage() {
    echo "Usage: $(basename "$0") [--doctor] [--rebuild]"
    echo "  --doctor   print the arming table and exit (no server)"
    echo "  --rebuild  rebuild the frontend even if web/dist exists"
    exit 0
}

DOCTOR=0
REBUILD=0
while [[ $# -gt 0 ]]; do
    case $1 in
        --doctor) DOCTOR=1; shift ;;
        --rebuild) REBUILD=1; shift ;;
        -h|--help) usage ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
done

# The library refuses to guess a filesystem root; empty means the real one.
export CONTROL_PANEL_ROOT="${CONTROL_PANEL_ROOT-}"

if [[ $DOCTOR -eq 1 ]]; then
    exec python3 -m control_panel doctor
fi

if [[ $REBUILD -eq 1 || ! -d "$SCRIPT_DIR/web/dist" ]]; then
    echo "Building the frontend (pnpm: npm cannot install @kuhyx/web-ui)..."
    pnpm --dir "$SCRIPT_DIR/web" install --frozen-lockfile
    pnpm --dir "$SCRIPT_DIR/web" run build
fi

exec python3 -m control_panel serve --port "$PORT"
