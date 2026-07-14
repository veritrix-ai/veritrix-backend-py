from __future__ import annotations

import os
from datetime import UTC, datetime

import httpx
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from ingest.auth import get_org_id_from_api_key
from ingest.clickhouse import ClickHouseClient, get_clickhouse_client, reset_clickhouse_client
from ingest.main import app
from ingest.postgres import dispose_engine, lookup_org_id
from shared.config import get_settings


TEST_API_KEY = "ao_live_7f3a9c2e1b8d4f6a5e0c9b2a1d8e7f6b60f6fec"


def sample_span() -> dict[str, object]:
    now = datetime.now(tz=UTC).isoformat()
    return {
        "trace_id": "integration-trace",
        "span_id": f"integration-span-{now}",
        "name": "integration-span",
        "start_time": now,
        "end_time": now,
        "status": "ok",
        "attributes": {
            "agentops.agent_id": "integration-agent",
            "agentops.agent_name": "Integration Agent",
            "agentops.run_id": "integration-run",
            "agentops.framework": "manual",
            "agentops.span_type": "agent",
            "agentops.duration_ms": 5,
        },
        "input_preview": "in",
        "output_preview": "out",
    }


async def clickhouse_is_available() -> bool:
    settings = get_settings()
    url = f"http://{settings.clickhouse_host}:{settings.clickhouse_port}/?query=SELECT%201"
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(url)
            return response.status_code == 200
    except Exception:
        return False


async def postgres_is_available() -> bool:
    settings = get_settings()
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    try:
        async with engine.connect() as connection:
            await connection.exec_driver_sql("SELECT 1")
        return True
    except Exception:
        return False
    finally:
        await engine.dispose()


integration = pytest.mark.integration


@pytest.fixture
async def integration_client() -> AsyncClient:
    reset_clickhouse_client()
    clickhouse = get_clickhouse_client()
    await clickhouse.ensure_schema()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

    app.dependency_overrides.clear()
    await dispose_engine()
    reset_clickhouse_client()


@integration
@pytest.mark.skipif(
    os.getenv("AGENTOPS_RUN_INTEGRATION") != "1",
    reason="Set AGENTOPS_RUN_INTEGRATION=1 with docker-compose running",
)
@pytest.mark.asyncio
async def test_ingest_spans_with_real_services(integration_client: AsyncClient) -> None:
    if not await clickhouse_is_available() or not await postgres_is_available():
        pytest.skip("ClickHouse or PostgreSQL is unavailable")

    response = await integration_client.post(
        "/v1/spans",
        json={"spans": [sample_span()]},
        headers={"Authorization": f"Bearer {TEST_API_KEY}"},
    )
    assert response.status_code == 202
    assert response.json()["accepted"] == 1

    settings = get_settings()
    query = (
        "SELECT count() FROM agentops.spans "
        "WHERE run_id = 'integration-run' FORMAT JSON"
    )
    async with httpx.AsyncClient(timeout=10.0) as client:
        result = await client.get(
            f"http://{settings.clickhouse_host}:{settings.clickhouse_port}/",
            params={"query": query},
        )
    assert result.status_code == 200
    payload = result.json()
    assert payload["data"][0]["count()"] >= "1"


@integration
@pytest.mark.skipif(
    os.getenv("AGENTOPS_RUN_INTEGRATION") != "1",
    reason="Set AGENTOPS_RUN_INTEGRATION=1 with docker-compose running",
)
@pytest.mark.asyncio
async def test_lookup_org_id_from_postgres() -> None:
    if not await postgres_is_available():
        pytest.skip("PostgreSQL is unavailable")

    settings = get_settings()
    session_factory = async_sessionmaker(create_async_engine(settings.database_url), expire_on_commit=False)
    async with session_factory() as session:
        org_id = await lookup_org_id(session, TEST_API_KEY)
    assert org_id == "11111111-1111-1111-1111-111111111111"
