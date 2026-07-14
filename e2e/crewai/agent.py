#!/usr/bin/env python3
"""
Minimal CrewAI crew — E2E test for AgentOps CrewAI integration.

agentops.init() auto-patches Crew.__init__ to inject step_callback spans.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

E2E_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(E2E_ROOT))

from lib.constants import (  # noqa: E402
    DEFAULT_API_KEY,
    DEFAULT_INGEST_ENDPOINT,
    DEFAULT_ORG_ID,
    repo_root,
    setup_sdk_path,
)

setup_sdk_path()

from dotenv import load_dotenv  # noqa: E402

import agentops  # noqa: E402
from agentops.config import get_config  # noqa: E402

load_dotenv(E2E_ROOT / ".env")
load_dotenv(repo_root() / ".env")

API_KEY = os.getenv("AGENTOPS_API_KEY", DEFAULT_API_KEY)
INGEST_ENDPOINT = os.getenv("AGENTOPS_ENDPOINT", DEFAULT_INGEST_ENDPOINT)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

DEFAULT_TOPIC = "observability for AI agents"

try:
    from crewai import Agent, Crew, Process, Task  # type: ignore[import-untyped]
except ImportError as exc:
    raise SystemExit(
        "Missing dependency: pip install 'crewai>=0.28.0' python-dotenv"
    ) from exc


def build_crew(*, topic: str, verbose: bool) -> Crew:
    researcher = Agent(
        role="Research Analyst",
        goal="Gather concise facts about {topic}",
        backstory="You produce short, factual research notes.",
        verbose=verbose,
        allow_delegation=False,
    )
    writer = Agent(
        role="Content Writer",
        goal="Summarize research into one clear sentence",
        backstory="You write brief, accurate summaries.",
        verbose=verbose,
        allow_delegation=False,
    )

    research_task = Task(
        description=(
            "Research {topic}. Return exactly 3 short bullet points — no preamble."
        ),
        expected_output="Three bullet points of facts about the topic",
        agent=researcher,
    )
    summary_task = Task(
        description=(
            "Using the research, write one sentence (under 200 characters) "
            "explaining {topic}."
        ),
        expected_output="One concise sentence",
        agent=writer,
    )

    return Crew(
        agents=[researcher, writer],
        tasks=[research_task, summary_task],
        process=Process.sequential,
        verbose=verbose,
    )


def print_verification_commands(trace_id: str) -> None:
    print()
    print("Spans sent. Verify with:")
    print(f'  curl "http://localhost:8000/v1/traces?org_id={DEFAULT_ORG_ID}"')
    print(f'  curl "http://localhost:8000/v1/traces/{trace_id}"')
    print(f'  curl "http://localhost:8000/v1/traces/{trace_id}/graph"')
    print()
    print("Look for framework=crewai and agent roles: Research Analyst, Content Writer.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a minimal CrewAI crew with AgentOps.")
    parser.add_argument(
        "--topic",
        default=DEFAULT_TOPIC,
        help=f"Topic for the crew to research (default: {DEFAULT_TOPIC!r})",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Reduce CrewAI verbose logging",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not OPENAI_API_KEY:
        raise SystemExit(
            "OPENAI_API_KEY is required. Export it or add it to backend/e2e/.env"
        )

    os.environ.setdefault("OPENAI_API_KEY", OPENAI_API_KEY)
    # Keep demo runs fast and cheap.
    os.environ.setdefault("OPENAI_MODEL_NAME", "gpt-4o-mini")

    print("Initializing AgentOps SDK (CrewAI integration)...")
    agentops.init(
        api_key=API_KEY,
        endpoint=INGEST_ENDPOINT,
        default_tags=["e2e-test", "crewai"],
        framework="crewai",
        agent_name="CrewAI E2E",
    )

    trace_id = get_config().trace_id
    print(f"AgentOps trace_id: {trace_id}")
    print(f"Ingest endpoint: {INGEST_ENDPOINT}")
    print(f"Topic: {args.topic}")
    print()

    crew = build_crew(topic=args.topic, verbose=not args.quiet)

    try:
        print("Running crew.kickoff()...")
        result = crew.kickoff(inputs={"topic": args.topic})
        print()
        print("Crew result:")
        print(result)
    finally:
        print()
        print("Flushing spans to ingest API...")
        agentops.end()

    print_verification_commands(trace_id)


if __name__ == "__main__":
    main()
