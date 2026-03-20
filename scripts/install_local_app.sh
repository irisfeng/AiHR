#!/usr/bin/env bash

set -euo pipefail

BENCH_DIR="${BENCH_DIR:-$HOME/frappe-bench}"
SITE_NAME="${SITE_NAME:-development.localhost}"
APP_DIR="${APP_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
APP_NAME="aihr"

if ! command -v bench >/dev/null 2>&1; then
  echo "bench is required. Run this script inside a Frappe development container or shell."
  exit 1
fi

if [ ! -d "$BENCH_DIR" ]; then
  echo "Bench directory not found: $BENCH_DIR"
  exit 1
fi

if [ ! -d "$BENCH_DIR/apps/$APP_NAME" ]; then
  ln -s "$APP_DIR" "$BENCH_DIR/apps/$APP_NAME"
fi

"$BENCH_DIR/env/bin/pip" install -e "$BENCH_DIR/apps/$APP_NAME"

cd "$BENCH_DIR"
bench --site "$SITE_NAME" install-app "$APP_NAME" || true
bench --site "$SITE_NAME" migrate
bench build --app "$APP_NAME"

echo "AIHR installed on site $SITE_NAME"

