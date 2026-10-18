#!/bin/bash

# ============================================================================
# Set up the dedicated virtualenv that hosts the token-dashboard MCP server
# and register it with Claude Code at USER scope (it is useful from every
# repo, not just this one, so there is deliberately no repo .mcp.json).
#
# The server only talks HTTP to the running dashboard (127.0.0.1:8760), so the
# venv holds just `mcp` + `control_panel_mcp`; the dashboard stays stdlib-only.
#
# Idempotent: safe to re-run to pick up dependency changes.
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR
PKG_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
readonly PKG_DIR
readonly VENV_DIR="${HOME}/.venvs/control-panel-mcp"
readonly SERVER_NAME="token-dashboard"

main() {
    echo "== Setting up MCP venv at ${VENV_DIR} =="
    if [[ ! -d "${VENV_DIR}" ]]; then
        python3 -m venv "${VENV_DIR}"
    fi
    "${VENV_DIR}/bin/pip" install --quiet --upgrade pip
    "${VENV_DIR}/bin/pip" install --quiet -e "${PKG_DIR}[test]"
    "${VENV_DIR}/bin/python" -c "import mcp, control_panel_mcp"

    echo "== Registering '${SERVER_NAME}' at user scope =="
    claude mcp remove --scope user "${SERVER_NAME}" >/dev/null 2>&1 || true
    claude mcp add --scope user "${SERVER_NAME}" -- \
        "${VENV_DIR}/bin/python" -m control_panel_mcp._mcp
    claude mcp get "${SERVER_NAME}"
}

main "$@"
