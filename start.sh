#!/usr/bin/env bash
set -euo pipefail

# App Store Top 30 - 极简一键启动脚本
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

# 清理旧端口
if command -v lsof &> /dev/null; then
    PIDS=$(lsof -ti:8080 2>/dev/null || true)
    if [ -n "$PIDS" ]; then
        echo "🧹 释放旧服务进程 (Port 8080): $PIDS"
        kill -9 $PIDS 2>/dev/null || true
    fi
fi

LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "0.0.0.0")

echo "=================================================="
echo "🚀 正在启动 App Store Top 30 看板服务..."
echo "=================================================="
echo "🌐 本地访问: http://127.0.0.1:8080"
echo "🌐 局域网访问: http://${LOCAL_IP}:8080"
echo "=================================================="

exec python3 -m appstore_top30 dashboard --host 0.0.0.0 --port 8080
