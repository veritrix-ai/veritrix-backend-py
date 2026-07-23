#!/usr/bin/env python3
"""
Airline customer service agent — E2E test for AgentOps.

Uses the OpenAI Agents SDK (multi-agent handoffs) and sends spans to the
local ingest API via the AgentOps Python SDK.

See README.md in this directory for setup and usage.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import random
import sys
import uuid
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
from pydantic import BaseModel  # noqa: E402

import veritrix  # noqa: E402
from veritrix.config import get_config  # noqa: E402

load_dotenv(E2E_ROOT / ".env")
load_dotenv(repo_root() / ".env")

DEMO_MESSAGES = [
    "What is the baggage allowance for my flight?",
    "I want to change my seat to 12A. My confirmation number is ABC123.",
]

API_KEY = os.getenv("VERITRIX_API_KEY") or os.getenv("AGENTOPS_API_KEY", DEFAULT_API_KEY)
INGEST_ENDPOINT = os.getenv("VERITRIX_ENDPOINT") or os.getenv("VERITRIX_ENDPOINT") or os.getenv("AGENTOPS_ENDPOINT", DEFAULT_INGEST_ENDPOINT)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

try:
    from agents import (  # type: ignore[import-untyped]
        Agent,
        HandoffOutputItem,
        ItemHelpers,
        MessageOutputItem,
        RunContextWrapper,
        Runner,
        ToolCallItem,
        ToolCallOutputItem,
        TResponseInputItem,
        function_tool,
        handoff,
        trace as agents_trace,
    )
    from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX  # type: ignore[import-untyped]
except ImportError as exc:
    raise SystemExit(
        "Missing dependency: pip install openai-agents python-dotenv"
    ) from exc


class AirlineAgentContext(BaseModel):
    passenger_name: str | None = None
    confirmation_number: str | None = None
    seat_number: str | None = None
    flight_number: str | None = None


@function_tool(name_override="faq_lookup_tool", description_override="Lookup frequently asked questions.")
async def faq_lookup_tool(question: str) -> str:
    if "bag" in question or "baggage" in question:
        return (
            "You are allowed to bring one bag on the plane. "
            "It must be under 50 pounds and 22 inches x 14 inches x 9 inches."
        )
    if "seats" in question or "plane" in question:
        return (
            "There are 120 seats on the plane. "
            "There are 22 business class seats and 98 economy seats. "
            "Exit rows are rows 4 and 16. "
            "Rows 5-8 are Economy Plus, with extra legroom."
        )
    if "wifi" in question:
        return "We have free wifi on the plane, join Airline-Wifi"
    return "I'm sorry, I don't know the answer to that question."


@function_tool
async def update_seat(
    context: RunContextWrapper[AirlineAgentContext],
    confirmation_number: str,
    new_seat: str,
) -> str:
    context.context.confirmation_number = confirmation_number
    context.context.seat_number = new_seat
    assert context.context.flight_number is not None, "Flight number is required"
    return f"Updated seat to {new_seat} for confirmation number {confirmation_number}"


async def on_seat_booking_handoff(context: RunContextWrapper[AirlineAgentContext]) -> None:
    context.context.flight_number = f"FLT-{random.randint(100, 999)}"


def build_agents() -> Agent[AirlineAgentContext]:
    faq_agent = Agent[AirlineAgentContext](
        name="FAQ Agent",
        handoff_description="A helpful agent that can answer questions about the airline.",
        instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
        You are an FAQ agent. If you are speaking to a customer, you probably were transferred from the triage agent.
        Use the following routine to support the customer.
        # Routine
        1. Identify the last question asked by the customer.
        2. Use the faq lookup tool to answer the question. Do not rely on your own knowledge.
        3. If you cannot answer the question, transfer back to the triage agent.""",
        tools=[faq_lookup_tool],
    )

    seat_booking_agent = Agent[AirlineAgentContext](
        name="Seat Booking Agent",
        handoff_description="A helpful agent that can update a seat on a flight.",
        instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
        You are a seat booking agent. If you are speaking to a customer, you probably were transferred from the triage agent.
        Use the following routine to support the customer.
        # Routine
        1. Ask for their confirmation number.
        2. Ask the customer what their desired seat number is.
        3. Use the update seat tool to update the seat on the flight.
        If the customer asks a question that is not related to the routine, transfer back to the triage agent.""",
        tools=[update_seat],
    )

    triage_agent = Agent[AirlineAgentContext](
        name="Triage Agent",
        handoff_description="A triage agent that can delegate a customer's request to the appropriate agent.",
        instructions=(
            f"{RECOMMENDED_PROMPT_PREFIX} "
            "You are a helpful triaging agent. You can use your tools to delegate questions to other appropriate agents."
        ),
        handoffs=[
            faq_agent,
            handoff(agent=seat_booking_agent, on_handoff=on_seat_booking_handoff),
        ],
    )

    faq_agent.handoffs.append(triage_agent)
    seat_booking_agent.handoffs.append(triage_agent)
    return triage_agent


def print_agent_output(new_items: list[object]) -> None:
    for new_item in new_items:
        agent_name = new_item.agent.name  # type: ignore[attr-defined]
        if isinstance(new_item, MessageOutputItem):
            print(f"{agent_name}: {ItemHelpers.text_message_output(new_item)}")
        elif isinstance(new_item, HandoffOutputItem):
            print(f"Handed off from {new_item.source_agent.name} to {new_item.target_agent.name}")
        elif isinstance(new_item, ToolCallItem):
            print(f"{agent_name}: Calling a tool")
        elif isinstance(new_item, ToolCallOutputItem):
            print(f"{agent_name}: Tool call output: {new_item.output}")
        else:
            print(f"{agent_name}: Skipping item: {new_item.__class__.__name__}")


async def run_turn(
    *,
    current_agent: Agent[AirlineAgentContext],
    input_items: list[TResponseInputItem],
    context: AirlineAgentContext,
    conversation_id: str,
    user_input: str,
    turn_index: int,
) -> tuple[Agent[AirlineAgentContext], list[TResponseInputItem]]:
    input_items.append({"content": user_input, "role": "user"})

    with veritrix.trace(
        f"turn-{turn_index}",
        span_type="agent",
        input_data={"message": user_input, "conversation_id": conversation_id},
    ):
        with agents_trace("Customer service", group_id=conversation_id):
            result = await Runner.run(current_agent, input_items, context=context)

    print_agent_output(result.new_items)
    return result.last_agent, result.to_input_list()


async def run_conversation(*, interactive: bool) -> str:
    if not OPENAI_API_KEY:
        raise SystemExit(
            "OPENAI_API_KEY is required. Export it or add it to backend/e2e/.env"
        )

    os.environ.setdefault("OPENAI_API_KEY", OPENAI_API_KEY)

    print("Initializing Veritrix SDK...")
    veritrix.init(
        api_key=API_KEY,
        endpoint=INGEST_ENDPOINT,
        default_tags=["customer-service-agent", "openai-agents", "agentops-example"],
        framework="manual",
        agent_name="Customer Service",
    )

    config = get_config()
    trace_id = config.trace_id
    print(f"AgentOps trace_id: {trace_id}")
    print(f"Ingest endpoint: {INGEST_ENDPOINT}")
    print()

    current_agent = build_agents()
    input_items: list[TResponseInputItem] = []
    context = AirlineAgentContext()
    conversation_id = uuid.uuid4().hex[:16]
    turn_index = 0

    try:
        if interactive:
            print("Interactive mode — type 'quit' to end.\n")
            while True:
                user_input = input("You: ").strip()
                if not user_input:
                    continue
                if user_input.lower() in {"quit", "exit", "q"}:
                    break
                turn_index += 1
                current_agent, input_items = await run_turn(
                    current_agent=current_agent,
                    input_items=input_items,
                    context=context,
                    conversation_id=conversation_id,
                    user_input=user_input,
                    turn_index=turn_index,
                )
                print()
        else:
            print("Demo mode — running scripted messages.\n")
            for message in DEMO_MESSAGES:
                print(f"You: {message}")
                turn_index += 1
                current_agent, input_items = await run_turn(
                    current_agent=current_agent,
                    input_items=input_items,
                    context=context,
                    conversation_id=conversation_id,
                    user_input=message,
                    turn_index=turn_index,
                )
                print()
    finally:
        print("Flushing spans to ingest API...")
        veritrix.end()

    print_verification_commands(trace_id)
    return trace_id


def print_verification_commands(trace_id: str) -> None:
    print()
    print("Spans sent. Verify with:")
    print(f'  curl "http://localhost:8000/v1/traces?org_id={DEFAULT_ORG_ID}"')
    print(f'  curl "http://localhost:8000/v1/traces/{trace_id}"')
    print(f'  curl "http://localhost:8000/v1/traces/{trace_id}/graph"')


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the airline customer service test agent.")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run scripted messages instead of interactive chat.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    asyncio.run(run_conversation(interactive=not args.demo))


if __name__ == "__main__":
    main()
