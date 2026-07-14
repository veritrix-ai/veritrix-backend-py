#!/usr/bin/env bash
# Deprecated: use backend/e2e/manual/validate.sh
exec "$(cd "$(dirname "$0")/.." && pwd)/e2e/manual/validate.sh" "$@"
