from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.auth import get_optional_org_scope, resolve_org_id
from api.models import (
    AgentListResponse,
    MetricsOverviewData,
    SpanStatus,
    TraceDetail,
    TraceGraphResponse,
    TraceListResponse,
)
from api.services.traces import get_trace_service

router = APIRouter(tags=["traces"])


@router.get("/v1/traces", response_model=TraceListResponse)
async def list_traces(
    org_id: str = Depends(resolve_org_id),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    status: SpanStatus | None = Query(None),
) -> TraceListResponse:
    return await get_trace_service().list_traces(
        org_id,
        limit=limit,
        offset=offset,
        status=status,
    )


@router.get("/v1/traces/{trace_id}", response_model=TraceDetail)
async def get_trace(
    trace_id: str,
    org_scope: str | None = Depends(get_optional_org_scope),
) -> TraceDetail:
    trace = await get_trace_service().get_trace(trace_id, org_scope)
    if trace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "trace not found"})
    return trace


@router.get("/v1/traces/{trace_id}/graph", response_model=TraceGraphResponse)
async def get_trace_graph(
    trace_id: str,
    org_scope: str | None = Depends(get_optional_org_scope),
) -> TraceGraphResponse:
    trace = await get_trace_service().get_trace(trace_id, org_scope)
    if trace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "trace not found"})
    return await get_trace_service().get_trace_graph(trace_id, org_scope)
