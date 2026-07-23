from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import httpx

from shared.config import Settings, get_settings
from shared.span_schema import SpanSchema

SPANS_TABLE = "spans"

CREATE_SPANS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS {database}.spans
(
    trace_id String,
    span_id String,
    parent_span_id Nullable(String),
    agent_id String,
    agent_name String,
    run_id String,
    framework LowCardinality(String),
    span_type LowCardinality(String),
    start_time DateTime64(3, 'UTC'),
    end_time DateTime64(3, 'UTC'),
    duration_ms UInt32,
    status LowCardinality(String),
    error_message Nullable(String),
    attributes String,
    input_preview String,
    output_preview String,
    org_id String,
    created_at DateTime DEFAULT now()
)
ENGINE = MergeTree()
ORDER BY (org_id, run_id, start_time)
PARTITION BY toYYYYMM(start_time)
"""


class ClickHouseClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    @property
    def _base_url(self) -> str:
        return f"http://{self._settings.clickhouse_host}:{self._settings.clickhouse_port}"

    def _auth(self) -> httpx.BasicAuth | None:
        if self._settings.clickhouse_password:
            return httpx.BasicAuth(self._settings.clickhouse_user, self._settings.clickhouse_password)
        return None

    async def _exec(self, client: httpx.AsyncClient, query: str) -> str:
        response = await client.post(
            self._base_url,
            params={"query": query},
            auth=self._auth(),
        )
        if response.is_error:
            raise RuntimeError(
                f"ClickHouse error ({response.status_code}): {response.text.strip()}"
            )
        return response.text

    async def ensure_schema(self) -> None:
        """Create DB/table, and recreate spans if existing table is unreadable.

        After ClickHouse OOM / crashloop on Render, MergeTree metadata can be
        left in a state where CREATE IF NOT EXISTS succeeds but SELECT returns 500.
        """
        database = self._settings.clickhouse_db
        create_db = f"CREATE DATABASE IF NOT EXISTS {database}"
        create_table = CREATE_SPANS_TABLE_SQL.format(database=database)
        probe = f"SELECT count() FROM {database}.{SPANS_TABLE}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            await self._exec(client, create_db)
            await self._exec(client, create_table)
            try:
                await self._exec(client, probe)
            except RuntimeError as first_error:
                # Corrupted / unreadable table after OOM — drop and recreate.
                await self._exec(client, f"DROP TABLE IF EXISTS {database}.{SPANS_TABLE}")
                await self._exec(client, create_table)
                try:
                    await self._exec(client, probe)
                except RuntimeError as second_error:
                    raise RuntimeError(
                        f"ClickHouse spans table unreadable after recreate. "
                        f"first={first_error}; second={second_error}"
                    ) from second_error

    async def insert_spans(self, org_id: str, spans: list[SpanSchema]) -> None:
        if not spans:
            return

        rows = [self._span_to_row(span, org_id) for span in spans]
        payload = "\n".join(json.dumps(row, default=str) for row in rows)
        query = f"INSERT INTO {self._settings.clickhouse_db}.{SPANS_TABLE} FORMAT JSONEachRow"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self._base_url,
                params={"query": query},
                content=payload,
                auth=self._auth(),
            )
            response.raise_for_status()

    def _span_to_row(self, span: SpanSchema, org_id: str) -> dict[str, Any]:
        attributes = span.attributes
        end_time = span.end_time or span.start_time
        duration_ms = attributes.get("agentops.duration_ms")
        if duration_ms is None:
            duration_ms = max(int((end_time - span.start_time).total_seconds() * 1000), 0)

        return {
            "trace_id": span.trace_id,
            "span_id": span.span_id,
            "parent_span_id": span.parent_span_id,
            "agent_id": str(attributes["agentops.agent_id"]),
            "agent_name": str(attributes["agentops.agent_name"]),
            "run_id": str(attributes["agentops.run_id"]),
            "framework": str(attributes["agentops.framework"]),
            "span_type": str(attributes["agentops.span_type"]),
            "start_time": _format_clickhouse_datetime(span.start_time),
            "end_time": _format_clickhouse_datetime(end_time),
            "duration_ms": int(duration_ms),
            "status": span.status,
            "error_message": span.error_message,
            "attributes": json.dumps(attributes, default=str),
            "input_preview": span.input_preview,
            "output_preview": span.output_preview,
            "org_id": org_id,
        }


def _format_clickhouse_datetime(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    else:
        value = value.astimezone(UTC)
    return value.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


_clickhouse_client: ClickHouseClient | None = None


def get_clickhouse_client() -> ClickHouseClient:
    global _clickhouse_client
    if _clickhouse_client is None:
        _clickhouse_client = ClickHouseClient()
    return _clickhouse_client


def reset_clickhouse_client() -> None:
    global _clickhouse_client
    _clickhouse_client = None
