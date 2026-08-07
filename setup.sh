#!/usr/bin/env bash
set -euo pipefail

# App Store Top 30 - 极简一键安装与启动脚本
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

echo "=================================================="
echo "🚀 正在为您初始化 App Store Top 30 监控分析系统..."
echo "=================================================="

# 1. 检查 Python3 环境
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未检测到 Python3，请先安装 Python 3.8 或更高版本！"
    exit 1
fi

PYTHON_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "✅ 检测到 Python 版本: $PYTHON_VER"

# 2. 创建必备工作目录
mkdir -p data logs reports

# 3. 清理可能残留的 8080 端口占用
echo "🧹 检查并释放 8080 端口..."
if command -v lsof &> /dev/null; then
    PIDS=$(lsof -ti:8080 2>/dev/null || true)
    if [ -n "$PIDS" ]; then
        echo "   杀死旧端口占用进程: $PIDS"
        kill -9 $PIDS 2>/dev/null || true
    fi
fi

# 4. 检查 SQLite 数据库状态与数据抓取
DB_FILE="$PROJECT_DIR/data/appstore_top30.db"
if [ ! -f "$DB_FILE" ]; then
    echo "📦 正在执行首次数据拉取与数据库初始化..."
    python3 -m appstore_top30 run || true
fi

# 5. 获取本机 IP 地址
LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "0.0.0.0")

echo ""
echo "=================================================="
echo "✨ 安装与初始化完成！正在启动 Web 看板服务..."
echo "=================================================="
echo "🌐 本地访问地址: http://127.0.0.1:8080"
echo "🌐 局域网访问地址: http://${LOCAL_IP}:8080"
echo "=================================================="
echo ""

# 启动 Server 绑定到 0.0.0.0 确保全局可访问
exec python3 -m appstore_top30 dashboard --host 0.0.0.0 --port 8080
