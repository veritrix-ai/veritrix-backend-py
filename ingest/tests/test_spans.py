from __future__ import annotations

from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient

from ingest.main import app
from ingest.rate_limit import RateLimiter, reset_rate_limiter
from shared.span_schema import SpanSchema


TEST_API_KEY = "ao_live_7f3a9c2e1b8d4f6a5e0c9b2a1d8e7f6b60f6fec"
TEST_ORG_ID = "11111111-1111-1111-1111-111111111111"


def sample_span(**overrides: object) -> dict[str, object]:
    now = datetime.now(tz=UTC).isoformat()
    payload: dict[str, object] = {
        "trace_id": "trace-1",
        "span_id": "span-1",
        "name": "test-span",
        "start_time": now,
        "end_time": now,
        "status": "ok",
        "attributes": {
            "agentops.agent_id": "agent-1",
            "agentops.agent_name": "Research Analyst",
            "agentops.run_id": "run-1",
            "agentops.framework": "crewai",
            "agentops.span_type": "agent",
            "agentops.duration_ms": 12,
        },
        "input_preview": "hello",
        "output_preview": "world",
    }
    payload.update(overrides)
    return payload


class FakeClickHouseClient:
    def __init__(self) -> None:
        self.inserted: list[tuple[str, list[SpanSchema]]] = []

    async def ensure_schema(self) -> None:
        return None

    async def insert_spans(self, org_id: str, spans: list[SpanSchema]) -> None:
        self.inserted.append((org_id, spans))


@pytest.fixture(autouse=True)
def reset_limits() -> None:
    reset_rate_limiter()


@pytest.fixture
def fake_clickhouse(monkeypatch: pytest.MonkeyPatch) -> FakeClickHouseClient:
    client = FakeClickHouseClient()
    monkeypatch.setattr("ingest.routes.spans.get_clickhouse_client", lambda: client)
    monkeypatch.setattr("ingest.main.get_clickhouse_client", lambda: client)
    return client


@pytest.fixture
async def client(fake_clickhouse: FakeClickHouseClient) -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as http_client:
        yield http_client


@pytest.fixture
async def authorized_client(client: AsyncClient) -> AsyncClient:
    async def fake_org_id() -> str:
        return TEST_ORG_ID

    from ingest.auth import get_org_id_from_api_key

    app.dependency_overrides[get_org_id_from_api_key] = fake_org_id
    yield client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_health(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_ingest_spans_returns_202(authorized_client: AsyncClient) -> None:
    response = await authorized_client.post(
        "/v1/spans",
        json={"spans": [sample_span()]},
        headers={"Authorization": f"Bearer {TEST_API_KEY}"},
    )

    assert response.status_code == 202
    assert response.json() == {"accepted": 1}


@pytest.mark.asyncio
async def test_ingest_spans_requires_api_key(client: AsyncClient) -> None:
    response = await client.post("/v1/spans", json={"spans": [sample_span()]})
    assert response.status_code == 401
    assert response.json() == {"error": "invalid api key"}


@pytest.mark.asyncio
async def test_ingest_spans_rejects_missing_attributes(authorized_client: AsyncClient) -> None:
    invalid_span = sample_span()
    invalid_span["attributes"] = {"agentops.agent_id": "agent-1"}

    response = await authorized_client.post(
        "/v1/spans",
        json={"spans": [invalid_span]},
        headers={"Authorization": f"Bearer {TEST_API_KEY}"},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_ingest_spans_rejects_empty_batch(authorized_client: AsyncClient) -> None:
    response = await authorized_client.post(
        "/v1/spans",
        json={"spans": []},
        headers={"Authorization": f"Bearer {TEST_API_KEY}"},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_ingest_spans_rate_limited(authorized_client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    import ingest.rate_limit as rate_limit_module

    monkeypatch.setattr(rate_limit_module, "_rate_limiter", RateLimiter(limit_per_minute=1))

    headers = {"Authorization": f"Bearer {TEST_API_KEY}"}
    first = await authorized_client.post("/v1/spans", json={"spans": [sample_span()]}, headers=headers)
    second = await authorized_client.post(
        "/v1/spans",
        json={"spans": [sample_span(span_id="span-2")]},
        headers=headers,
    )

    assert first.status_code == 202
    assert second.status_code == 429
    assert second.json() == {"error": "rate limited"}
