from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

from api.auth import AuthContext, get_auth_context, require_authenticated_user
from api.db.postgres import get_session
from api.main import app


class FakeSession:
    def __init__(self) -> None:
        self.committed = False

    async def begin(self):  # type: ignore[no-untyped-def]
        class _Txn:
            async def __aenter__(self_inner):  # type: ignore[no-untyped-def]
                return self_inner

            async def __aexit__(self_inner, *args):  # type: ignore[no-untyped-def]
                return False

        return _Txn()

    async def execute(self, query, params=None):  # type: ignore[no-untyped-def]
        sql = str(query)
        clerk_user_id = (params or {}).get("clerk_user_id")

        class Result:
            def mappings(self):  # type: ignore[no-untyped-def]
                if "FROM users u" in sql and clerk_user_id == "user-1":
                    return self

                class Empty:
                    def first(self):  # type: ignore[no-untyped-def]
                        return None

                return Empty()

            def first(self):  # type: ignore[no-untyped-def]
                return None

        if "FROM users u" in sql and clerk_user_id == "user-provisioned":
            row = {
                "clerk_user_id": "user-provisioned",
                "email": "founder@example.com",
                "org_id": "org-1",
                "org_name": "Acme AI",
            }

            class RowResult:
                def mappings(self):  # type: ignore[no-untyped-def]
                    class M:
                        def first(self):  # type: ignore[no-untyped-def]
                            return row

                    return M()

            return RowResult()

        if "FROM projects" in sql:
            class ProjectResult:
                def mappings(self):  # type: ignore[no-untyped-def]
                    class M:
                        def __iter__(self):  # type: ignore[no-untyped-def]
                            return iter([{"id": "project-1", "name": "Default Project"}])

                    return M()

            return ProjectResult()

        if "FROM api_keys ak" in sql:
            class KeyResult:
                def mappings(self):  # type: ignore[no-untyped-def]
                    class M:
                        def __iter__(self):  # type: ignore[no-untyped-def]
                            return iter(
                                [
                                    {
                                        "id": "key-1",
                                        "key_value": "ao_live_test_key",
                                        "name": "Default Key",
                                        "project_name": "Default Project",
                                    }
                                ]
                            )

                    return M()

            return KeyResult()

        return Result()


async def fake_get_session() -> AsyncGenerator[FakeSession, None]:
    yield FakeSession()


@pytest.fixture(autouse=True)
def auth_user() -> None:
    async def authenticated() -> AuthContext:
        return AuthContext(
            user_id="user-provisioned",
            org_id="org-1",
            email="founder@example.com",
        )

    app.dependency_overrides[get_auth_context] = authenticated
    app.dependency_overrides[require_authenticated_user] = authenticated
    app.dependency_overrides[get_session] = fake_get_session
    yield
    app.dependency_overrides.clear()


@pytest.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as http_client:
        yield http_client


@pytest.mark.asyncio
async def test_get_me_returns_provisioned_profile(client: AsyncClient) -> None:
    response = await client.get("/v1/me")
    assert response.status_code == 200
    body = response.json()
    assert body["provisioned"] is True
    assert body["org_id"] == "org-1"
    assert body["org_name"] == "Acme AI"
    assert body["api_keys"][0]["key_value"] == "ao_live_test_key"


@pytest.mark.asyncio
async def test_onboarding_is_idempotent(client: AsyncClient) -> None:
    response = await client.post(
        "/v1/onboarding",
        json={"org_name": "Acme AI", "email": "founder@example.com"},
    )
    assert response.status_code == 201
    assert response.json()["org_id"] == "org-1"
