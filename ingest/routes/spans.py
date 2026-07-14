from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from ingest.auth import get_org_id_from_api_key
from ingest.clickhouse import get_clickhouse_client
from ingest.models import AcceptedResponse, ErrorResponse
from ingest.rate_limit import check_rate_limit
from shared.span_schema import SpanBatch

router = APIRouter(tags=["spans"])


@router.post(
    "/v1/spans",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=AcceptedResponse,
    responses={
        401: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
    },
)
async def ingest_spans(
    batch: SpanBatch,
    background_tasks: BackgroundTasks,
    org_id: str = Depends(get_org_id_from_api_key),
) -> AcceptedResponse:
    if not check_rate_limit(org_id):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"error": "rate limited"},
        )

    clickhouse = get_clickhouse_client()
    background_tasks.add_task(clickhouse.insert_spans, org_id, batch.spans)
    return AcceptedResponse(accepted=len(batch.spans))
