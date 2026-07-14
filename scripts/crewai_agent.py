#!/usr/bin/env python3
"""Deprecated: use backend/e2e/crewai/agent.py or ./e2e/crewai/run.sh"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

agent = Path(__file__).resolve().parent.parent / "e2e" / "crewai" / "agent.py"
sys.argv[0] = str(agent)
runpy.run_path(str(agent), run_name="__main__")
