from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from api.auth import AuthContext, get_auth_context
from api.db.postgres import DatabaseUnavailableError, is_db_connection_error, run_db
from api.main import app


def test_is_db_connection_error_detects_refused() -> None:
    assert is_db_connection_error(ConnectionRefusedError(61, "Connection refused"))
    assert is_db_connection_error(DatabaseUnavailableError("database unavailable"))
    assert not is_db_connection_error(ValueError("nope"))


@pytest.mark.asyncio
async def test_run_db_maps_connection_errors() -> None:
    async def boom() -> None:
        raise ConnectionRefusedError(61, "Connection refused")

    with pytest.raises(DatabaseUnavailableError, match="database unavailable"):
        await run_db(boom)


@pytest.mark.asyncio
async def test_database_unavailable_returns_503() -> None:
    async def failing_auth() -> AuthContext:
        raise DatabaseUnavailableError("database unavailable")

    app.dependency_overrides[get_auth_context] = failing_auth
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get("/v1/me")
        assert response.status_code == 503
        assert response.json() == {"error": "database unavailable"}
    finally:
        app.dependency_overrides.clear()
