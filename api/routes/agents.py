from __future__ import annotations

from fastapi import APIRouter, Depends

from api.auth import resolve_org_id
from api.models import AgentListResponse
from api.services.traces import get_trace_service

router = APIRouter(tags=["agents"])


@router.get("/v1/agents", response_model=AgentListResponse)
async def list_agents(org_id: str = Depends(resolve_org_id)) -> AgentListResponse:
    return await get_trace_service().list_agents(org_id)
