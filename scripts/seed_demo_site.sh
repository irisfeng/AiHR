#!/usr/bin/env bash

set -euo pipefail

CONTAINER_NAME="${CONTAINER_NAME:-devcontainer-example-frappe-1}"
BENCH_DIR="${BENCH_DIR:-/workspace/development/frappe-bench}"
SITE_NAME="${SITE_NAME:-development.localhost}"
COMPANY_NAME="${COMPANY_NAME:-AIHR Demo}"

docker exec "$CONTAINER_NAME" bash -lc "
  cd '$BENCH_DIR' &&
  bench --site '$SITE_NAME' execute aihr.api.demo.seed_demo_recruitment_data --kwargs '{\"company\": \"$COMPANY_NAME\"}'
"
