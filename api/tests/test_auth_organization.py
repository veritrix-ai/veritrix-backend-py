from __future__ import annotations

import pytest
from fastapi.security import HTTPAuthorizationCredentials

from api import auth as auth_module


@pytest.mark.asyncio
async def test_clerk_organization_is_mapped_to_internal_org(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(auth_module, "_clerk_auth_enabled", lambda: True)
    monkeypatch.setattr(
        auth_module,
        "_verify_clerk_token",
        lambda _: {"sub": "user-1", "org_id": "org_clerk_1", "email": "owner@example.com"},
    )

    async def lookup_clerk_org(_session: object, clerk_org_id: str) -> str | None:
        assert clerk_org_id == "org_clerk_1"
        return "11111111-1111-1111-1111-111111111111"

    monkeypatch.setattr(auth_module, "lookup_org_id_for_clerk_org", lookup_clerk_org)

    context = await auth_module.get_auth_context(
        HTTPAuthorizationCredentials(scheme="Bearer", credentials="session-token"),
        object(),  # type: ignore[arg-type] - authentication lookup test double
    )

    assert context.org_id == "11111111-1111-1111-1111-111111111111"
    assert context.clerk_org_id == "org_clerk_1"


@pytest.mark.asyncio
async def test_user_mapping_remains_fallback_without_active_clerk_org(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(auth_module, "_clerk_auth_enabled", lambda: True)
    monkeypatch.setattr(
        auth_module,
        "_verify_clerk_token",
        lambda _: {"sub": "user-1", "email": "owner@example.com"},
    )

    async def lookup_user(_session: object, clerk_user_id: str) -> str | None:
        assert clerk_user_id == "user-1"
        return "11111111-1111-1111-1111-111111111111"

    monkeypatch.setattr(auth_module, "lookup_org_id_for_clerk_user", lookup_user)

    context = await auth_module.get_auth_context(
        HTTPAuthorizationCredentials(scheme="Bearer", credentials="session-token"),
        object(),  # type: ignore[arg-type] - authentication lookup test double
    )

    assert context.org_id == "11111111-1111-1111-1111-111111111111"
    assert context.clerk_org_id is None


@pytest.mark.asyncio
async def test_unmapped_active_clerk_org_falls_back_to_user_org(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(auth_module, "_clerk_auth_enabled", lambda: True)
    monkeypatch.setattr(
        auth_module,
        "_verify_clerk_token",
        lambda _: {"sub": "user-1", "org_id": "org_unlinked"},
    )

    async def no_clerk_mapping(_session: object, _clerk_org_id: str) -> None:
        return None

    async def lookup_user(_session: object, _clerk_user_id: str) -> str:
        return "11111111-1111-1111-1111-111111111111"

    monkeypatch.setattr(auth_module, "lookup_org_id_for_clerk_org", no_clerk_mapping)
    monkeypatch.setattr(auth_module, "lookup_org_id_for_clerk_user", lookup_user)

    context = await auth_module.get_auth_context(
        HTTPAuthorizationCredentials(scheme="Bearer", credentials="session-token"),
        object(),  # type: ignore[arg-type] - authentication lookup test double
    )

    assert context.org_id == "11111111-1111-1111-1111-111111111111"
    assert context.clerk_org_id == "org_unlinked"
