#!/usr/bin/env bash
# Full manual E2E: health → agent → curl verification
set -euo pipefail
cd "$(dirname "$0")"
source ../lib/common.sh

check_api_health
echo "==> Run manual test agent"
python3 agent.py
echo ""
echo "==> Wait for ClickHouse background insert"
sleep 2
verify_traces_via_curl 5
