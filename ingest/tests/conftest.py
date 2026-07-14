from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession


class FakeSession:
    async def execute(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        class Result:
            def first(self) -> None:
                return None

        return Result()


async def fake_get_session() -> AsyncGenerator[AsyncSession, None]:
    yield FakeSession()  # type: ignore[misc]


@pytest.fixture(autouse=True)
def mock_postgres_session(request: pytest.FixtureRequest) -> None:
    if request.node.get_closest_marker("integration"):
        return

    from ingest.main import app
    from ingest.postgres import get_session

    app.dependency_overrides[get_session] = fake_get_session
    yield
    app.dependency_overrides.pop(get_session, None)
