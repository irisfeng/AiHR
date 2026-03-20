#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
FRAPPE_DOCKER_DIR="${FRAPPE_DOCKER_DIR:-$ROOT_DIR/.frappe_docker}"
FRAPPE_DOCKER_REPO="${FRAPPE_DOCKER_REPO:-https://github.com/frappe/frappe_docker.git}"
APPS_JSON_SOURCE="$ROOT_DIR/infra/apps.json"
APPS_JSON_TARGET="$FRAPPE_DOCKER_DIR/development/apps.json"

if ! command -v git >/dev/null 2>&1; then
  echo "git is required."
  exit 1
fi

if [ ! -d "$FRAPPE_DOCKER_DIR/.git" ]; then
  git clone --depth 1 "$FRAPPE_DOCKER_REPO" "$FRAPPE_DOCKER_DIR"
else
  echo "Using existing frappe_docker checkout at $FRAPPE_DOCKER_DIR"
fi

mkdir -p "$FRAPPE_DOCKER_DIR/development"
cp "$APPS_JSON_SOURCE" "$APPS_JSON_TARGET"

cat <<EOF
Frappe Docker is prepared at:
  $FRAPPE_DOCKER_DIR

apps.json has been copied to:
  $APPS_JSON_TARGET

Suggested next steps:
  1. cd "$FRAPPE_DOCKER_DIR"
  2. Open the project with Dev Containers, or enter your Frappe dev shell
  3. Run the official installer with development/apps.json
  4. Install AIHR with scripts/install_local_app.sh
EOF

