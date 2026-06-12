#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
SERVICE_NAME="technews-frontend.service"
PORT="3012"
HEALTH_URL="http://127.0.0.1:${PORT}/technews/"
PROD_DIST_DIR="$FRONTEND_DIR/.next-prod"
BUILD_LOG="$PROJECT_ROOT/.runtime/frontend.user.log"
START_LOG="/tmp/technews-frontend-3012.log"

log() {
  printf '[restart_frontend] %s\n' "$*"
}

show_failure_help() {
  log "frontend restart failed. recent logs:"
  journalctl --user -u "$SERVICE_NAME" --no-pager -n 120 || true
  log "runtime frontend log tail:"
  tail -n 120 "$BUILD_LOG" 2>/dev/null || true
  tail -n 120 "$PROJECT_ROOT/.runtime/frontend.systemd.log" 2>/dev/null || true
  tail -n 120 "$START_LOG" 2>/dev/null || true
}

trap 'show_failure_help' ERR

build_frontend() {
  log "building frontend"
  (
    cd "$FRONTEND_DIR"
    npm run build:prod:app > "$BUILD_LOG" 2>&1
  )

  if [[ ! -f "$PROD_DIST_DIR/BUILD_ID" ]]; then
    log "BUILD_ID missing after build"
    tail -n 120 "$BUILD_LOG" 2>/dev/null || true
    return 1
  fi

  if [[ ! -f "$PROD_DIST_DIR/build-manifest.json" ]]; then
    log "build-manifest.json missing after build"
    tail -n 120 "$BUILD_LOG" 2>/dev/null || true
    return 1
  fi
}

log "project root: $PROJECT_ROOT"
log "stopping $SERVICE_NAME"
systemctl --user stop "$SERVICE_NAME" || true
systemctl --user reset-failed "$SERVICE_NAME" || true

log "killing listeners on port $PORT"
fuser -k "${PORT}/tcp" >/dev/null 2>&1 || true
pkill -f "next-server.*${PORT}" || true
sleep 2

if ss -ltn | grep -q ":${PORT} "; then
  log "port $PORT still in use after cleanup"
  ss -ltnp | grep ":${PORT}" || true
  exit 1
fi

log "cleaning old production build output"
rm -rf "$PROD_DIST_DIR"

log "checking node_modules"
test -x "$FRONTEND_DIR/node_modules/.bin/next"

build_frontend
"$PROJECT_ROOT/scripts/publish_frontend_static.sh"

log "starting $SERVICE_NAME"
systemctl --user start "$SERVICE_NAME"
sleep 3

log "service status"
systemctl --user status "$SERVICE_NAME" --no-pager -l | sed -n '1,80p'

log "listener check"
ss -ltnp | grep ":${PORT}"

log "http check"
curl -I -fsS "$HEALTH_URL"

log "frontend restart ok"
