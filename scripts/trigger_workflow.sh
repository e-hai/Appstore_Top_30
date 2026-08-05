#!/usr/bin/env bash
set -euo pipefail

TOKEN="${GITHUB_PAT:-}"
REPO="${GITHUB_REPO:-e-hai/Appstore_Top_30}"
WORKFLOW="${GITHUB_WORKFLOW:-daily.yml}"

if [ -z "$TOKEN" ]; then
  echo "GITHUB_PAT is required" >&2
  exit 1
fi

curl -fsS -o /dev/null -w "%{http_code}\n" -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/vnd.github+json" \
  -H "Content-Type: application/json" \
  "https://api.github.com/repos/$REPO/actions/workflows/$WORKFLOW/dispatches" \
  -d '{"ref":"main"}'

echo "Workflow dispatch requested for $REPO/$WORKFLOW"
