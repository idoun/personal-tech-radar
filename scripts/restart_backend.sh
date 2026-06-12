#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
SERVICE_NAME="technews-backend.service"
PORT="8010"
HEALTH_URL="http://127.0.0.1:${PORT}/health"
OPENAPI_URL="http://127.0.0.1:${PORT}/openapi.json"

log() {
  printf '[restart_backend] %s\n' "$*"
}

show_failure_help() {
  log "backend restart failed. recent logs:"
  journalctl --user -u "$SERVICE_NAME" --no-pager -n 80 || true
  log "direct uvicorn traceback attempt:"
  (
    cd "$BACKEND_DIR"
    . .venv/bin/activate
    uvicorn app.main:app --host 127.0.0.1 --port "$PORT"
  ) || true
}

trap 'show_failure_help' ERR

log "project root: $PROJECT_ROOT"
log "stopping $SERVICE_NAME"
systemctl --user stop "$SERVICE_NAME" || true

log "killing listeners on port $PORT"
fuser -k "${PORT}/tcp" >/dev/null 2>&1 || true
pkill -f "uvicorn app.main:app --host 127.0.0.1 --port ${PORT}" || true
sleep 2

if ss -ltn | grep -q ":${PORT} "; then
  log "port $PORT still in use after cleanup"
  ss -ltnp | grep ":${PORT}" || true
  exit 1
fi

log "checking backend venv"
test -x "$BACKEND_DIR/.venv/bin/uvicorn"

log "starting $SERVICE_NAME"
systemctl --user start "$SERVICE_NAME"
sleep 2

log "service status"
systemctl --user status "$SERVICE_NAME" --no-pager -l

log "health check"
curl -fsS "$HEALTH_URL" >/dev/null

log "openapi check"
TMP_OPENAPI="$(mktemp)"
curl -fsS "$OPENAPI_URL" -o "$TMP_OPENAPI"

log "issue route check"
python3 - "$TMP_OPENAPI" <<'PY'
import json, sys
with open(sys.argv[1], 'r', encoding='utf-8') as fh:
    obj = json.load(fh)
paths = sorted(k for k in obj.get('paths', {}) if 'issues' in k)
for path in paths:
    print(path)
PY
rm -f "$TMP_OPENAPI"

log "backend restart ok"
