#!/usr/bin/env bash

set -euo pipefail

load_project_env() {
  local root_dir="$1"
  local env_file

  for env_file in "$root_dir/.env" "$root_dir/.env.local"; do
    if [ -f "$env_file" ]; then
      set -a
      # shellcheck disable=SC1090
      . "$env_file"
      set +a
    fi
  done
}


build_docker_env_args() {
  DOCKER_ENV_ARGS=()

  while IFS= read -r env_name; do
    if [ -n "${!env_name:-}" ]; then
      DOCKER_ENV_ARGS+=("-e" "$env_name=${!env_name}")
    fi
  done < <(env | cut -d= -f1 | sort -u | grep -E '^(AIHR_|MINERU_)' || true)
}
