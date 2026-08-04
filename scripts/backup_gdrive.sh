#!/usr/bin/env bash
set -euo pipefail

REMOTE="${RCLONE_REMOTE:-gdrive:appstore-top30}"
CONFIG_ARGS=()
if [[ -n "${RCLONE_CONFIG:-}" ]]; then
  CONFIG_ARGS=(--config "$RCLONE_CONFIG")
fi

mkdir -p data reports
rclone "${CONFIG_ARGS[@]}" copy data/appstore_top30.db "$REMOTE/data/"
rclone "${CONFIG_ARGS[@]}" sync reports/ "$REMOTE/reports/"

echo "Google Drive backup complete: $REMOTE"
