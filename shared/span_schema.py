from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

SpanStatus = Literal["ok", "error"]
SpanType = Literal["agent", "tool", "llm", "delegation"]
Framework = Literal["langchain", "crewai", "manual"]

REQUIRED_ATTRIBUTES = (
    "agentops.agent_id",
    "agentops.agent_name",
    "agentops.run_id",
    "agentops.framework",
    "agentops.span_type",
)

MAX_BATCH_SIZE = 500


class SpanSchema(BaseModel):
    """OTel-compatible span shape shared by SDK, ingest, and app API."""

    trace_id: str
    span_id: str
    parent_span_id: str | None = None
    name: str
    start_time: datetime
    end_time: datetime | None = None
    status: SpanStatus = "ok"
    error_message: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    input_preview: str = ""
    output_preview: str = ""

    @field_validator("attributes")
    @classmethod
    def validate_required_attributes(cls, attributes: dict[str, Any]) -> dict[str, Any]:
        missing = [key for key in REQUIRED_ATTRIBUTES if key not in attributes]
        if missing:
            missing_list = ", ".join(missing)
            raise ValueError(f"missing required attributes: {missing_list}")
        return attributes


class SpanBatch(BaseModel):
    spans: list[SpanSchema]

    @field_validator("spans")
    @classmethod
    def validate_batch_size(cls, spans: list[SpanSchema]) -> list[SpanSchema]:
        if len(spans) > MAX_BATCH_SIZE:
            raise ValueError(f"batch exceeds maximum of {MAX_BATCH_SIZE} spans")
        if len(spans) == 0:
            raise ValueError("batch must contain at least one span")
        return spans
