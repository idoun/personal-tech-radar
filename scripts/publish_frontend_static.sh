#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
PROD_DIST_DIR="$FRONTEND_DIR/.next-prod"
PUBLIC_STATIC_DIR="/var/www/technews-next-static"

if [[ ! -d "$PROD_DIST_DIR/static" ]]; then
  echo "missing prod static directory: $PROD_DIST_DIR/static" >&2
  exit 1
fi

sudo mkdir -p "$PUBLIC_STATIC_DIR"
sudo rsync -a --delete "$PROD_DIST_DIR/static/" "$PUBLIC_STATIC_DIR/"
