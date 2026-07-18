from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from api.models import ProjectSummary

DEMO_ORG_ID = "11111111-1111-1111-1111-111111111111"


@pytest.fixture
def mock_project_service(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    service = AsyncMock()
    service.rename_project.return_value = ProjectSummary(
        id="22222222-2222-2222-2222-222222222222",
        name="Renamed Project",
    )
    monkeypatch.setattr("api.routes.projects.project_service", service)
    return service


@pytest.mark.asyncio
async def test_health(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_list_traces(client: AsyncClient, mock_trace_service) -> None:
    response = await client.get(f"/v1/traces?org_id={DEMO_ORG_ID}")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["traces"][0]["trace_id"] == "trace-1"
    mock_trace_service.list_traces.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_trace(client: AsyncClient, mock_trace_service) -> None:
    response = await client.get("/v1/traces/trace-1")
    assert response.status_code == 200
    assert response.json()["trace_id"] == "trace-1"


@pytest.mark.asyncio
async def test_get_trace_not_found(client: AsyncClient, mock_trace_service) -> None:
    mock_trace_service.get_trace.return_value = None
    response = await client.get("/v1/traces/missing")
    assert response.status_code == 404
    assert response.json() == {"error": "trace not found"}


@pytest.mark.asyncio
async def test_get_trace_graph(client: AsyncClient, mock_trace_service) -> None:
    response = await client.get("/v1/traces/trace-1/graph")
    assert response.status_code == 200
    assert response.json() == {"nodes": [], "edges": []}


@pytest.mark.asyncio
async def test_list_agents(client: AsyncClient, mock_trace_service) -> None:
    response = await client.get(f"/v1/agents?org_id={DEMO_ORG_ID}")
    assert response.status_code == 200
    assert response.json()["agents"][0]["agent_name"] == "Research Analyst"


@pytest.mark.asyncio
async def test_metrics_overview(client: AsyncClient, mock_trace_service) -> None:
    response = await client.get(f"/v1/metrics/overview?org_id={DEMO_ORG_ID}")
    assert response.status_code == 200
    assert response.json()["overview"]["total_events"] == 3


@pytest.mark.asyncio
async def test_rename_project(client: AsyncClient, mock_project_service: AsyncMock) -> None:
    response = await client.patch(
        f"/v1/projects/project-1?org_id={DEMO_ORG_ID}",
        json={"name": "Renamed Project"},
    )
    assert response.status_code == 200
    assert response.json() == {
        "id": "22222222-2222-2222-2222-222222222222",
        "name": "Renamed Project",
    }
    mock_project_service.rename_project.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_project(client: AsyncClient, mock_project_service: AsyncMock) -> None:
    response = await client.request(
        "DELETE",
        f"/v1/projects/project-1?org_id={DEMO_ORG_ID}",
        json={"confirm_name": "Default Project"},
    )
    assert response.status_code == 204
    mock_project_service.delete_project.assert_awaited_once()


@pytest.mark.asyncio
async def test_link_clerk_organization(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = AsyncMock()
    monkeypatch.setattr("api.routes.organization.org_service", service)

    response = await client.patch(
        f"/v1/organization/clerk-link?org_id={DEMO_ORG_ID}",
        json={"clerk_org_id": "org_clerk_acme"},
    )

    assert response.status_code == 204
    service.link_clerk_organization.assert_awaited_once()
