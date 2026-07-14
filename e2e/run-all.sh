#!/usr/bin/env bash
# Run all E2E suites that do not require OpenAI.
set -euo pipefail
cd "$(dirname "$0")"

echo "========================================"
echo " AgentOps E2E — manual suite"
echo "========================================"
./manual/validate.sh

echo ""
echo "========================================"
echo " Skipping LLM suites (need OPENAI_API_KEY)"
echo " Run: ./customer-service/validate.sh"
echo " Run: ./crewai/validate.sh"
echo "========================================"
