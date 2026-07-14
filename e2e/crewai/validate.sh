#!/usr/bin/env bash
# Full CrewAI E2E: health → crew → curl verification
set -euo pipefail
cd "$(dirname "$0")"
source ../lib/common.sh

if [[ -z "${OPENAI_API_KEY:-}" ]]; then
  if [[ -f ../.env ]]; then
    set -a
    # shellcheck disable=SC1091
    source ../.env
    set +a
  fi
fi

if [[ -z "${OPENAI_API_KEY:-}" ]]; then
  echo "ERROR: OPENAI_API_KEY is required."
  echo "  export OPENAI_API_KEY=...  OR  cp ../.env.example ../.env and edit"
  exit 1
fi

check_api_health
echo "==> Run CrewAI test crew"
python3 agent.py --quiet
echo ""
echo "==> Wait for ClickHouse background insert"
sleep 3
verify_traces_via_curl 5
