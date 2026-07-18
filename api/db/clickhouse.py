from __future__ import annotations

import json
from typing import Any

import httpx

from shared.config import Settings, get_settings


class ClickHouseReader:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    @property
    def _base_url(self) -> str:
        return f"http://{self._settings.clickhouse_host}:{self._settings.clickhouse_port}"

    def _auth(self) -> httpx.BasicAuth | None:
        if self._settings.clickhouse_password:
            return httpx.BasicAuth(
                self._settings.clickhouse_user, self._settings.clickhouse_password
            )
        return None

    async def query(self, sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        query_params: dict[str, Any] = {"query": sql}
        if params:
            for key, value in params.items():
                query_params[f"param_{key}"] = value

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Use GET for read-only queries; some ClickHouse setups reject POST without a body.
            response = await client.get(self._base_url, params=query_params, auth=self._auth())
            response.raise_for_status()
            payload = response.json()
            return payload.get("data", [])

    async def query_scalar(self, sql: str, params: dict[str, Any] | None = None) -> Any:
        rows = await self.query(sql, params)
        if not rows:
            return None
        return next(iter(rows[0].values()))


_reader: ClickHouseReader | None = None


def get_clickhouse_reader() -> ClickHouseReader:
    global _reader
    if _reader is None:
        _reader = ClickHouseReader()
    return _reader


def reset_clickhouse_reader() -> None:
    global _reader
    _reader = None


def parse_attributes(raw: str | dict[str, Any] | None) -> dict[str, Any]:
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}
