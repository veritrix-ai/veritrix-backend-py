from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import AuthContext, require_authenticated_user, resolve_org_id
from api.db.postgres import get_session
from api.models import (
    CreateInviteRequest,
    OrgInvite,
    OrgMember,
    OrgMembersResponse,
    OrganizationDetail,
    UpdateMemberRoleRequest,
    UpdateOrganizationRequest,
)
from api.services import organization as org_service

router = APIRouter(prefix="/v1/organization", tags=["organization"])


@router.get("", response_model=OrganizationDetail)
async def get_organization(
    org_id: str = Depends(resolve_org_id),
    _: AuthContext = Depends(require_authenticated_user),
    session: AsyncSession = Depends(get_session),
) -> OrganizationDetail:
    return await org_service.get_organization(session, org_id)


@router.patch("", response_model=OrganizationDetail)
async def update_organization(
    body: UpdateOrganizationRequest,
    org_id: str = Depends(resolve_org_id),
    _: AuthContext = Depends(require_authenticated_user),
    session: AsyncSession = Depends(get_session),
) -> OrganizationDetail:
    return await org_service.update_organization(session, org_id, body)


@router.get("/members", response_model=OrgMembersResponse)
async def list_members(
    org_id: str = Depends(resolve_org_id),
    _: AuthContext = Depends(require_authenticated_user),
    session: AsyncSession = Depends(get_session),
) -> OrgMembersResponse:
    return await org_service.list_members_and_invites(session, org_id)


@router.post("/invites", response_model=OrgInvite, status_code=status.HTTP_201_CREATED)
async def create_invite(
    body: CreateInviteRequest,
    org_id: str = Depends(resolve_org_id),
    auth: AuthContext = Depends(require_authenticated_user),
    session: AsyncSession = Depends(get_session),
) -> OrgInvite:
    return await org_service.create_invite(
        session,
        org_id,
        body,
        invited_by=auth.user_id,
    )


@router.patch("/members/{member_id}", response_model=OrgMember)
async def update_member_role(
    member_id: str,
    body: UpdateMemberRoleRequest,
    org_id: str = Depends(resolve_org_id),
    _: AuthContext = Depends(require_authenticated_user),
    session: AsyncSession = Depends(get_session),
) -> OrgMember:
    return await org_service.update_member_role(session, org_id, member_id, body)


@router.delete("/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def remove_member(
    member_id: str,
    org_id: str = Depends(resolve_org_id),
    _: AuthContext = Depends(require_authenticated_user),
    session: AsyncSession = Depends(get_session),
) -> Response:
    await org_service.remove_member(session, org_id, member_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/invites/{invite_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def revoke_invite(
    invite_id: str,
    org_id: str = Depends(resolve_org_id),
    _: AuthContext = Depends(require_authenticated_user),
    session: AsyncSession = Depends(get_session),
) -> Response:
    await org_service.revoke_invite(session, org_id, invite_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
