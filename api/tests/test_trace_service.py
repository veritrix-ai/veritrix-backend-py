from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from api.db.clickhouse import parse_attributes
from api.models import Span
from api.services.traces import TraceService, _derive_agents, _row_to_span


def test_parse_attributes_from_json_string() -> None:
    assert parse_attributes('{"agentops.tag": "crewai"}')["agentops.tag"] == "crewai"


def test_row_to_span_maps_clickhouse_row() -> None:
    span = _row_to_span(
        {
            "trace_id": "trace-1",
            "span_id": "span-1",
            "parent_span_id": None,
            "agent_id": "agent-1",
            "agent_name": "Research Analyst",
            "run_id": "run-1",
            "framework": "crewai",
            "span_type": "agent",
            "start_time": "2026-06-15 12:00:00.000",
            "end_time": "2026-06-15 12:00:02.500",
            "duration_ms": 2500,
            "status": "ok",
            "error_message": None,
            "attributes": '{"agentops.tag": "crewai"}',
            "input_preview": "hello",
            "output_preview": "world",
        }
    )
    assert span.span_id == "span-1"
    assert span.framework == "crewai"
    assert span.attributes["agentops.tag"] == "crewai"


def test_row_to_span_extracts_token_usage() -> None:
    span = _row_to_span(
        {
            "trace_id": "trace-1",
            "span_id": "span-llm",
            "parent_span_id": None,
            "agent_id": "agent-1",
            "agent_name": "LLM",
            "run_id": "run-1",
            "framework": "manual",
            "span_type": "llm",
            "start_time": "2026-06-15 12:00:00.000",
            "end_time": "2026-06-15 12:00:01.000",
            "duration_ms": 1000,
            "status": "ok",
            "error_message": None,
            "attributes": '{"agentops.prompt_tokens": 100, "agentops.completion_tokens": 40, "agentops.model": "gpt-4o-mini"}',
            "input_preview": "",
            "output_preview": "",
        }
    )
    assert span.prompt_tokens == 100
    assert span.completion_tokens == 40
    assert span.total_tokens == 140
    assert span.cost_usd is not None
    assert span.cost_usd > 0


def test_derive_agents_links_tools_to_agents() -> None:
    spans = [
        Span(
            trace_id="t",
            span_id="agent",
            parent_span_id=None,
            agent_id="a1",
            agent_name="Agent",
            run_id="r",
            framework="crewai",
            span_type="agent",
            start_time="2026-06-15T12:00:00.000Z",
            end_time="2026-06-15T12:00:01.000Z",
            duration_ms=1000,
            status="ok",
            error_message=None,
            attributes={},
        ),
        Span(
            trace_id="t",
            span_id="tool",
            parent_span_id="agent",
            agent_id="a1",
            agent_name="web-search",
            run_id="r",
            framework="crewai",
            span_type="tool",
            start_time="2026-06-15T12:00:00.100Z",
            end_time="2026-06-15T12:00:00.800Z",
            duration_ms=700,
            status="ok",
            error_message=None,
            attributes={},
        ),
    ]
    agents = _derive_agents(spans)
    assert agents[0].name == "Agent"
    assert agents[0].tools == ["web-search"]


@pytest.mark.asyncio
async def test_trace_service_get_trace_returns_none_when_empty() -> None:
    reader = AsyncMock()
    reader.query.return_value = []
    service = TraceService(reader=reader)

    result = await service.get_trace("missing", "org-1")
    assert result is None
