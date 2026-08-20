#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
mkdir -p logs
python3 -m appstore_top30 run "$@" >> logs/daily.log 2>&1
python3 -m appstore_top30 play "$@" >> logs/daily.log 2>&1 || true
python3 -m appstore_top30 fetch-drivers "$@" >> logs/daily.log 2>&1 || true
python3 -m appstore_top30 export-pages --out docs >> logs/daily.log 2>&1 || true
