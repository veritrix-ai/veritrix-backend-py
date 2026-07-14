"""Shared constants for local E2E test agents."""

from __future__ import annotations

import sys
from pathlib import Path

DEFAULT_API_KEY = "ao_live_7f3a9c2e1b8d4f6a5e0c9b2a1d8e7f6b60f6fec"
DEFAULT_ORG_ID = "11111111-1111-1111-1111-111111111111"
DEFAULT_INGEST_ENDPOINT = "http://localhost:8001"
DEFAULT_APP_API_URL = "http://localhost:8000"


def repo_root() -> Path:
    # backend/e2e/lib/constants.py -> repo root is 3 levels up
    return Path(__file__).resolve().parents[3]


def setup_sdk_path() -> None:
    sdk_root = repo_root() / "sdk"
    sdk_str = str(sdk_root)
    if sdk_str not in sys.path:
        sys.path.insert(0, sdk_str)
