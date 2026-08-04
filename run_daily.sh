#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
mkdir -p logs
python3 -m appstore_top30 run "$@" >> logs/daily.log 2>&1
