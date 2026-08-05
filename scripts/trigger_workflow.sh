#!/usr/bin/env bash
set -euo pipefail

TOKEN="${GITHUB_PAT:-}"
REPO="${GITHUB_REPO:-e-hai/Appstore_Top_30}"
WORKFLOW="${GITHUB_WORKFLOW:-daily.yml}"
DATE="${GITHUB_DATE:-}"
STORES="${GITHUB_STORES:-both}"

if [ -z "$TOKEN" ]; then
  echo "GITHUB_PAT is required" >&2
  exit 1
fi

INPUTS=""
if [ -n "$DATE" ]; then
  INPUTS=",\"inputs\":{\"date\":\"$DATE\",\"stores\":\"$STORES\"}"
fi

curl -fsS -o /dev/null -w "%{http_code}\n" -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/vnd.github+json" \
  -H "Content-Type: application/json" \
  "https://api.github.com/repos/$REPO/actions/workflows/$WORKFLOW/dispatches" \
  -d "{\"ref\":\"main\"$INPUTS}"

echo "Workflow dispatch requested for $REPO/$WORKFLOW"
