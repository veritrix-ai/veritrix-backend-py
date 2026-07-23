#!/usr/bin/env python3
"""Minimal manual E2E agent — no OpenAI required."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

E2E_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(E2E_ROOT))

from lib.constants import (  # noqa: E402
    DEFAULT_API_KEY,
    DEFAULT_INGEST_ENDPOINT,
    DEFAULT_ORG_ID,
    setup_sdk_path,
)

setup_sdk_path()

import veritrix  # noqa: E402
from veritrix.config import get_config  # noqa: E402

API_KEY = os.getenv("VERITRIX_API_KEY") or os.getenv("AGENTOPS_API_KEY", DEFAULT_API_KEY)
ENDPOINT = os.getenv("VERITRIX_ENDPOINT") or os.getenv("VERITRIX_ENDPOINT") or os.getenv("AGENTOPS_ENDPOINT", DEFAULT_INGEST_ENDPOINT)


def main() -> None:
    print("Initializing Veritrix SDK (manual E2E)...")
    veritrix.init(
        api_key=API_KEY,
        endpoint=ENDPOINT,
        default_tags=["e2e-test", "manual"],
        framework="manual",
        agent_name="E2E Test Agent",
    )

    trace_id = get_config().trace_id
    print(f"Session trace_id / run_id: {trace_id}")

    with veritrix.trace(
        "research-step",
        span_type="agent",
        input_data={"query": "What are the top ML engineer roles?"},
    ):
        time.sleep(0.1)
        with veritrix.trace("web-search", span_type="tool", input_data="ML engineer jobs 2026"):
            time.sleep(0.05)
        with veritrix.trace("summarize", span_type="llm", input_data="Summarize search results"):
            time.sleep(0.05)

    print("Flushing spans...")
    veritrix.end()
    print_verification_commands(trace_id)


def print_verification_commands(trace_id: str) -> None:
    print()
    print("Done. Verify with:")
    print(f'  curl "http://localhost:8000/v1/traces?org_id={DEFAULT_ORG_ID}"')
    print(f'  curl "http://localhost:8000/v1/traces/{trace_id}"')
    print(f'  curl "http://localhost:8000/v1/traces/{trace_id}/graph"')


if __name__ == "__main__":
    main()
