from __future__ import annotations

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from api.auth import AuthContext, get_auth_context
from api.db.postgres import get_session
from api.main import app
from api.models import (
    AgentListResponse,
    AgentSummary,
    MetricsOverviewData,
    Span,
    SpanEndStateDistribution,
    TraceDetail,
    TraceGraphResponse,
    TraceListResponse,
    TraceMetrics,
    TraceSummary,
)


class FakeSession:
    async def execute(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        class Result:
            def first(self) -> None:
                return None

        return Result()


async def fake_get_session() -> AsyncGenerator[FakeSession, None]:
    yield FakeSession()


@pytest.fixture(autouse=True)
def bypass_auth() -> None:
    async def dev_auth() -> AuthContext:
        return AuthContext(
            user_id="dev-user",
            org_id="11111111-1111-1111-1111-111111111111",
            email="dev@agentops.local",
        )

    app.dependency_overrides[get_auth_context] = dev_auth
    app.dependency_overrides[get_session] = fake_get_session
    yield
    app.dependency_overrides.clear()


@pytest.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as http_client:
        yield http_client


DEMO_ORG_ID = "11111111-1111-1111-1111-111111111111"


@pytest.fixture
def mock_trace_service(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    service = AsyncMock()
    service.list_traces.return_value = TraceListResponse(
        traces=[
            TraceSummary(
                trace_id="trace-1",
                run_id="run-1",
                agent_name="Research Analyst",
                name="Research Analyst",
                status="ok",
                duration_ms=2500,
                span_count=3,
                start_time="2026-06-15T12:00:00.000Z",
            )
        ],
        total=1,
        metrics=TraceMetrics(
            total_cost_usd=0.0,
            tokens_generated=0,
            fail_rate=0.0,
            total_events=3,
        ),
    )
    service.get_trace.return_value = TraceDetail(
        trace_id="trace-1",
        run_id="run-1",
        spans=[
            Span(
                trace_id="trace-1",
                span_id="span-1",
                parent_span_id=None,
                agent_id="agent-1",
                agent_name="Research Analyst",
                run_id="run-1",
                framework="crewai",
                span_type="agent",
                start_time="2026-06-15T12:00:00.000Z",
                end_time="2026-06-15T12:00:02.500Z",
                duration_ms=2500,
                status="ok",
                error_message=None,
                attributes={"agentops.framework": "crewai"},
            )
        ],
    )
    service.get_trace_graph.return_value = TraceGraphResponse(nodes=[], edges=[])
    service.list_agents.return_value = AgentListResponse(
        agents=[
            AgentSummary(
                agent_id="agent-1",
                agent_name="Research Analyst",
                framework="crewai",
                total_runs=5,
                error_rate=0.0,
                avg_duration_ms=2500,
                last_seen="2026-06-15T12:00:00.000Z",
            )
        ]
    )
    service.get_metrics_overview.return_value = MetricsOverviewData(
        overview=TraceMetrics(
            total_cost_usd=0.0,
            tokens_generated=0,
            fail_rate=0.0,
            total_events=3,
            monthly_spans=3,
            monthly_span_limit=5000,
        ),
        span_end_states=[],
        span_end_states_distribution=SpanEndStateDistribution(success=3, indeterminate=0, fail=0),
        spans_per_trace=[],
        trace_duration_distribution=[],
        failed_spans=[],
        trace_cost_distribution=[],
    )

    monkeypatch.setattr("api.routes.traces.get_trace_service", lambda: service)
    monkeypatch.setattr("api.routes.agents.get_trace_service", lambda: service)
    monkeypatch.setattr("api.routes.metrics.get_trace_service", lambda: service)
    return service
