#!/usr/bin/env bash
set -euo pipefail

REMOTE="${RCLONE_REMOTE:-gdrive:appstore-top30}"
CONFIG_ARGS=()
if [[ -n "${RCLONE_CONFIG:-}" ]]; then
  CONFIG_ARGS=(--config "$RCLONE_CONFIG")
fi

# 性能优化参数：提高并发数、开启 fast-list 减少 API 检查次数、增大块大小
RCLONE_FLAGS=(--transfers 16 --checkers 32 --fast-list --drive-chunk-size 32M)

mkdir -p data reports
if [[ ${#CONFIG_ARGS[@]} -gt 0 ]]; then
  rclone "${CONFIG_ARGS[@]}" "${RCLONE_FLAGS[@]}" copy data/appstore_top30.db "$REMOTE/data/"
  rclone "${CONFIG_ARGS[@]}" "${RCLONE_FLAGS[@]}" sync reports/ "$REMOTE/reports/"
else
  rclone "${RCLONE_FLAGS[@]}" copy data/appstore_top30.db "$REMOTE/data/"
  rclone "${RCLONE_FLAGS[@]}" sync reports/ "$REMOTE/reports/"
fi

echo "Google Drive backup complete: $REMOTE"
