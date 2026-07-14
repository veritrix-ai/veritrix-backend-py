from __future__ import annotations

from fastapi import APIRouter, Depends

from api.auth import resolve_org_id
from api.models import MetricsOverviewData
from api.services.traces import get_trace_service

router = APIRouter(tags=["metrics"])


@router.get("/v1/metrics/overview", response_model=MetricsOverviewData)
async def get_metrics_overview(org_id: str = Depends(resolve_org_id)) -> MetricsOverviewData:
    return await get_trace_service().get_metrics_overview(org_id)
