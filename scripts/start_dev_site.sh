#!/usr/bin/env bash

set -euo pipefail

CONTAINER_NAME="${CONTAINER_NAME:-devcontainer-example-frappe-1}"
BENCH_DIR="${BENCH_DIR:-/workspace/development/frappe-bench}"
LOG_DIR="${LOG_DIR:-/workspace/development/logs}"
PORT="${PORT:-8000}"
HOST_PORT="${HOST_PORT:-18000}"
SITE_NAME="${SITE_NAME:-development.localhost}"

docker exec "$CONTAINER_NAME" bash -lc "
  mkdir -p '$LOG_DIR' '$BENCH_DIR/logs' &&
  pkill -f 'bench serve --port $PORT' >/dev/null 2>&1 || true &&
  cd '$BENCH_DIR' &&
  nohup bench serve --port '$PORT' --noreload > '$LOG_DIR/bench-serve.log' 2>&1 &
"

cat <<EOF
AIHR 本地开发站点已启动。

打开地址：
  http://$SITE_NAME:$HOST_PORT

如果需要看服务日志：
  docker exec $CONTAINER_NAME bash -lc 'tail -f $LOG_DIR/bench-serve.log'
EOF
