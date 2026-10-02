#!/bin/bash

# ============================================================================
# Install control-panel for this user: build the web UI, run the dashboard as
# a user service on 127.0.0.1:8760, and put its tray icon in the i3 bar.
# Writes only under $HOME. Rerunnable: every step is idempotent.
# ============================================================================

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly REPO_DIR
readonly UNIT="control-panel-web.service"
readonly UNIT_DIR="${HOME}/.config/systemd/user"
readonly TRAY_DIR="${HOME}/.config/i3/scripts"
readonly TRAY="control_panel_tray.py"
readonly I3_CONFIG="${HOME}/.config/i3/config"
readonly HEALTH_URL="http://127.0.0.1:8760/api/health"

log() { printf 'control-panel: %s\n' "$*"; }

require() {
    local tool
    for tool in "$@"; do
        command -v "$tool" >/dev/null || { log "missing $tool"; exit 1; }
    done
}

install_tray_deps() {
    # PyGObject + GTK3 + librsvg (the icon is an SVG) for the system python3.
    if ! /usr/bin/python3 -c 'import gi; gi.require_version("Gtk", "3.0")' 2>/dev/null; then
        sudo pacman -S --needed --noconfirm python-gobject gtk3 librsvg
    fi
}

build_web() {
    log "building the web UI (pnpm: npm cannot install @kuhyx/web-ui)"
    pnpm --dir "$REPO_DIR/web" install --frozen-lockfile
    pnpm --dir "$REPO_DIR/web" run build
}

install_unit() {
    mkdir -p "$UNIT_DIR"
    install -m 644 "$REPO_DIR/systemd/$UNIT" "$UNIT_DIR/$UNIT"
    systemctl --user daemon-reload
    systemctl --user enable "$UNIT"
    systemctl --user restart "$UNIT"
    local attempt
    for attempt in 1 2 3 4 5 6 7 8 9 10; do
        if curl -sf "$HEALTH_URL" >/dev/null; then
            log "dashboard up at http://127.0.0.1:8760/ (attempt $attempt)"
            return 0
        fi
        sleep 1
    done
    log "dashboard did not answer on $HEALTH_URL"
    systemctl --user status "$UNIT" --no-pager | tail -20
    exit 1
}

install_tray() {
    # Copied, not symlinked, matching leetcode-guard's and screen-locker's trays.
    mkdir -p "$TRAY_DIR"
    install -m 755 "$REPO_DIR/scripts/$TRAY" "$TRAY_DIR/$TRAY"
    local exec_line="exec --no-startup-id /usr/bin/python3 $TRAY_DIR/$TRAY"
    if [[ -f "$I3_CONFIG" ]] && ! grep -qF "$TRAY" "$I3_CONFIG"; then
        {
            printf '\n# control-panel fleet tray. Left-click opens the dashboard;\n'
            printf '# right-click lists every service and its own dashboards.\n'
            printf '%s\n' "$exec_line"
        } >> "$I3_CONFIG"
        log "added the tray to $I3_CONFIG (starts at next login)"
    else
        log "tray already referenced in $I3_CONFIG (or no i3 config found)"
    fi
}

main() {
    require pnpm curl systemctl install
    install_tray_deps
    build_web
    install_unit
    install_tray
    log "done. Check every link: python3 -m control_panel dashboards"
}

main "$@"
