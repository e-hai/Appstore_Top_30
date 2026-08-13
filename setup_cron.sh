#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DAILY_SCRIPT="${SCRIPT_DIR}/run_daily.sh"

echo "=================================================="
echo "⏰ 配置 App Store Top 30 & 20大休闲巨头 每日定时抓取..."
echo "=================================================="

# 给予 run_daily.sh 可执行权限
chmod +x "${DAILY_SCRIPT}"

# 设置 Crontab 任务: 每天上午 08:00 自动运行
CRON_JOB="0 8 * * * ${DAILY_SCRIPT}"

# 检查 crontab 中是否已存在
if crontab -l 2>/dev/null | grep -F "${DAILY_SCRIPT}" >/dev/null; then
  echo "✅ 定时任务已配置，无需重复添加："
  crontab -l | grep -F "${DAILY_SCRIPT}"
else
  (crontab -l 2>/dev/null || true; echo "${CRON_JOB}") | crontab -
  echo "🎉 定时任务配置成功！"
  echo "⏰ 触发时间: 每天上午 08:00"
  echo "📜 脚本路径: ${DAILY_SCRIPT}"
  echo "📁 日志存放: ${SCRIPT_DIR}/logs/daily.log"
fi

echo "=================================================="
