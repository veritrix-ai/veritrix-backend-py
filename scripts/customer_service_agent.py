#!/usr/bin/env python3
"""Deprecated: use backend/e2e/customer-service/agent.py or ./e2e/customer-service/run.sh"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

agent = Path(__file__).resolve().parent.parent / "e2e" / "customer-service" / "agent.py"
sys.argv[0] = str(agent)
if "--demo" not in sys.argv:
    sys.argv.append("--demo")
runpy.run_path(str(agent), run_name="__main__")
