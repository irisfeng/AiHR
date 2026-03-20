#!/usr/bin/env bash

set -euo pipefail

BENCH_DIR="${BENCH_DIR:-$HOME/frappe-bench}"
SITE_NAME="${SITE_NAME:-development.localhost}"
APP_DIR="${APP_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
APP_NAME="aihr"
APPS_TXT="$BENCH_DIR/sites/apps.txt"
BENCH_APPS_DIR="$BENCH_DIR/apps"

if ! command -v bench >/dev/null 2>&1; then
  echo "bench is required. Run this script inside a Frappe development container or shell."
  exit 1
fi

if [ ! -d "$BENCH_DIR" ]; then
  echo "Bench directory not found: $BENCH_DIR"
  exit 1
fi

if [ ! -d "$BENCH_DIR/sites/$SITE_NAME" ]; then
  echo "Site not found: $SITE_NAME"
  exit 1
fi

if [ ! -e "$BENCH_DIR/apps/$APP_NAME" ]; then
  ln -s "$APP_DIR" "$BENCH_DIR/apps/$APP_NAME"
fi

if [ ! -f "$APPS_TXT" ]; then
  echo "Bench apps registry not found: $APPS_TXT"
  exit 1
fi

python - "$APPS_TXT" "$APP_NAME" "$BENCH_APPS_DIR" <<'PY'
from pathlib import Path
import sys

apps_txt = Path(sys.argv[1])
target_app = sys.argv[2]
bench_apps_dir = Path(sys.argv[3])
known_apps = sorted(
    [path.name for path in bench_apps_dir.iterdir() if path.is_dir()],
    key=len,
    reverse=True,
)


def split_known_apps(raw_line: str) -> list[str]:
    if raw_line in known_apps:
        return [raw_line]

    remaining = raw_line
    parts: list[str] = []

    while remaining:
        matched = next((app for app in known_apps if remaining.startswith(app)), None)
        if not matched:
            return [raw_line]
        parts.append(matched)
        remaining = remaining[len(matched):]

    return parts


normalized: list[str] = []
for line in apps_txt.read_text().splitlines():
    raw = line.strip()
    if not raw:
        continue
    for part in split_known_apps(raw):
        if part not in normalized:
            normalized.append(part)

if target_app not in normalized:
    normalized.append(target_app)

apps_txt.write_text("\n".join(normalized) + "\n")
PY

"$BENCH_DIR/env/bin/pip" install -e "$BENCH_DIR/apps/$APP_NAME"

cd "$BENCH_DIR"

if bench --site "$SITE_NAME" list-apps | awk '{print $1}' | grep -qx "$APP_NAME"; then
  echo "$APP_NAME is already installed on $SITE_NAME"
else
  bench --site "$SITE_NAME" install-app "$APP_NAME"
fi

bench --site "$SITE_NAME" migrate

if find -L "$BENCH_DIR/apps/$APP_NAME" \
  \( -path "*/package.json" -o -path "*/public/js" -o -path "*/public/scss" \) \
  -print -quit | grep -q .; then
  bench build --app "$APP_NAME"
else
  echo "Skipping bench build for $APP_NAME (no frontend assets yet)."
fi

echo "AIHR installed on site $SITE_NAME"
