#!/usr/bin/env bash
# Shared helpers for E2E shell scripts. Source from other scripts:
#   source "$(dirname "$0")/../lib/common.sh"

E2E_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_ROOT="$(cd "${E2E_ROOT}/.." && pwd)"

export ORG_ID="${ORG_ID:-11111111-1111-1111-1111-111111111111}"
export API_KEY="${AGENTOPS_API_KEY:-ao_live_7f3a9c2e1b8d4f6a5e0c9b2a1d8e7f6b60f6fec}"
export INGEST_URL="${AGENTOPS_ENDPOINT:-http://localhost:8001}"
export APP_URL="${NEXT_PUBLIC_API_URL:-http://localhost:8000}"

check_api_health() {
  echo "==> Health checks"
  curl -sf "${INGEST_URL%/}/health" | grep -q '"status":"ok"' && echo "  Ingest API (${INGEST_URL}): OK"
  curl -sf "${APP_URL}/health" | grep -q '"status":"ok"' && echo "  App API (${APP_URL}): OK"
  echo ""
}

verify_traces_via_curl() {
  local limit="${1:-5}"
  echo "==> List traces"
  local traces_json
  traces_json=$(curl -sf "${APP_URL}/v1/traces?org_id=${ORG_ID}&limit=${limit}")
  echo "${traces_json}" | python3 -m json.tool

  local trace_id
  trace_id=$(echo "${traces_json}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['traces'][0]['trace_id'] if d.get('traces') else '')")

  if [[ -z "${trace_id}" ]]; then
    echo "ERROR: No traces found. Check ingest logs and ClickHouse."
    return 1
  fi

  echo ""
  echo "==> Trace detail (trace_id=${trace_id})"
  curl -sf "${APP_URL}/v1/traces/${trace_id}" | python3 -m json.tool | head -60

  echo ""
  echo "==> Trace graph"
  curl -sf "${APP_URL}/v1/traces/${trace_id}/graph" | python3 -m json.tool | head -40

  echo ""
  echo "==> Agents"
  curl -sf "${APP_URL}/v1/agents?org_id=${ORG_ID}" | python3 -m json.tool

  echo ""
  echo "E2E verification complete (trace_id=${trace_id})."
}
