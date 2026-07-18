from __future__ import annotations

from collections import deque

import pytest
from fastapi import HTTPException

from api.models import LinkClerkOrganizationRequest
from api.services.organization import link_clerk_organization


class Result:
    def __init__(self, value: object | None) -> None:
        self.value = value

    def mappings(self) -> Result:
        return self

    def first(self) -> object | None:
        return self.value


class Session:
    def __init__(self, *results: object | None) -> None:
        self.results = deque(results)
        self.committed = False

    async def execute(self, _query: object, _params: object = None) -> Result:
        return Result(self.results.popleft())

    async def commit(self) -> None:
        self.committed = True


@pytest.mark.asyncio
async def test_owner_can_link_clerk_organization() -> None:
    session = Session({"role": "owner"}, None, ("org-1",))

    await link_clerk_organization(
        session,  # type: ignore[arg-type] - focused SQLAlchemy session test double
        "11111111-1111-1111-1111-111111111111",
        "user-1",
        LinkClerkOrganizationRequest(clerk_org_id="org_clerk_acme"),
    )

    assert session.committed is True


@pytest.mark.asyncio
async def test_non_owner_cannot_link_clerk_organization() -> None:
    session = Session({"role": "member"})

    with pytest.raises(HTTPException) as exc_info:
        await link_clerk_organization(
            session,  # type: ignore[arg-type] - focused SQLAlchemy session test double
            "11111111-1111-1111-1111-111111111111",
            "user-2",
            LinkClerkOrganizationRequest(clerk_org_id="org_clerk_acme"),
        )

    assert exc_info.value.status_code == 403
    assert session.committed is False
