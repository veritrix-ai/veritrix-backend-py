from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.postgres import run_db
from api.models import (
    CreateInviteRequest,
    OrgInvite,
    OrgMember,
    OrgMembersResponse,
    OrganizationDetail,
    UpdateMemberRoleRequest,
    UpdateOrganizationRequest,
)


async def get_organization(session: AsyncSession, org_id: str) -> OrganizationDetail:
    async def _load() -> OrganizationDetail:
        result = await session.execute(
            text(
                """
                SELECT
                    o.id::text AS id,
                    o.name,
                    o.created_at::text AS created_at,
                    (
                        SELECT COUNT(*)::int FROM org_members m WHERE m.org_id = o.id
                    ) AS member_count,
                    (
                        SELECT COUNT(*)::int
                        FROM org_invites i
                        WHERE i.org_id = o.id AND i.status = 'pending'
                    ) AS pending_invite_count
                FROM orgs o
                WHERE o.id = :org_id
                LIMIT 1
                """
            ),
            {"org_id": org_id},
        )
        row = result.mappings().first()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "organization not found"},
            )
        return OrganizationDetail(
            id=row["id"],
            name=row["name"],
            created_at=row["created_at"],
            member_count=row["member_count"] or 0,
            pending_invite_count=row["pending_invite_count"] or 0,
        )

    return await run_db(_load)


async def update_organization(
    session: AsyncSession,
    org_id: str,
    body: UpdateOrganizationRequest,
) -> OrganizationDetail:
    async def _update() -> None:
        result = await session.execute(
            text(
                """
                UPDATE orgs
                SET name = :name
                WHERE id = :org_id
                RETURNING id
                """
            ),
            {"org_id": org_id, "name": body.name.strip()},
        )
        if result.first() is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "organization not found"},
            )
        await session.commit()

    await run_db(_update)
    return await get_organization(session, org_id)


async def list_members_and_invites(session: AsyncSession, org_id: str) -> OrgMembersResponse:
    async def _load() -> OrgMembersResponse:
        members_result = await session.execute(
            text(
                """
                SELECT
                    id::text AS id,
                    email,
                    role,
                    clerk_user_id,
                    created_at::text AS joined_at
                FROM org_members
                WHERE org_id = :org_id
                ORDER BY
                    CASE role
                        WHEN 'owner' THEN 0
                        WHEN 'admin' THEN 1
                        WHEN 'member' THEN 2
                        ELSE 3
                    END,
                    created_at ASC
                """
            ),
            {"org_id": org_id},
        )
        members = [
            OrgMember(
                id=row["id"],
                email=row["email"],
                role=row["role"],
                clerk_user_id=row["clerk_user_id"],
                joined_at=row["joined_at"],
            )
            for row in members_result.mappings()
        ]

        # Legacy fallback: orgs provisioned before org_members existed.
        if not members:
            legacy = await session.execute(
                text(
                    """
                    SELECT
                        u.id::text AS id,
                        u.email,
                        u.clerk_user_id,
                        u.created_at::text AS joined_at
                    FROM users u
                    WHERE u.org_id = :org_id
                    ORDER BY u.created_at ASC
                    """
                ),
                {"org_id": org_id},
            )
            members = [
                OrgMember(
                    id=row["id"],
                    email=row["email"],
                    role="owner",
                    clerk_user_id=row["clerk_user_id"],
                    joined_at=row["joined_at"],
                )
                for row in legacy.mappings()
            ]

        invites_result = await session.execute(
            text(
                """
                SELECT
                    id::text AS id,
                    email,
                    role,
                    status,
                    invited_by,
                    created_at::text AS created_at,
                    expires_at::text AS expires_at
                FROM org_invites
                WHERE org_id = :org_id
                  AND status = 'pending'
                ORDER BY created_at DESC
                """
            ),
            {"org_id": org_id},
        )
        invites = [
            OrgInvite(
                id=row["id"],
                email=row["email"],
                role=row["role"],
                status=row["status"],
                invited_by=row["invited_by"],
                created_at=row["created_at"],
                expires_at=row["expires_at"],
            )
            for row in invites_result.mappings()
        ]

        return OrgMembersResponse(members=members, invites=invites)

    return await run_db(_load)


async def create_invite(
    session: AsyncSession,
    org_id: str,
    body: CreateInviteRequest,
    *,
    invited_by: str | None,
) -> OrgInvite:
    email = body.email.strip().lower()

    async def _insert() -> OrgInvite:
        existing_member = await session.execute(
            text(
                """
                SELECT 1 FROM org_members
                WHERE org_id = :org_id AND lower(email) = :email
                LIMIT 1
                """
            ),
            {"org_id": org_id, "email": email},
        )
        if existing_member.first() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error": "user is already a member of this organization"},
            )

        existing_invite = await session.execute(
            text(
                """
                SELECT id::text FROM org_invites
                WHERE org_id = :org_id
                  AND lower(email) = :email
                  AND status = 'pending'
                LIMIT 1
                """
            ),
            {"org_id": org_id, "email": email},
        )
        if existing_invite.first() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error": "an invite is already pending for this email"},
            )

        result = await session.execute(
            text(
                """
                INSERT INTO org_invites (org_id, email, role, invited_by)
                VALUES (:org_id, :email, :role, :invited_by)
                RETURNING
                    id::text AS id,
                    email,
                    role,
                    status,
                    invited_by,
                    created_at::text AS created_at,
                    expires_at::text AS expires_at
                """
            ),
            {
                "org_id": org_id,
                "email": email,
                "role": body.role,
                "invited_by": invited_by,
            },
        )
        row = result.mappings().first()
        await session.commit()
        if row is None:
            raise RuntimeError("Failed to create invite")
        return OrgInvite(
            id=row["id"],
            email=row["email"],
            role=row["role"],
            status=row["status"],
            invited_by=row["invited_by"],
            created_at=row["created_at"],
            expires_at=row["expires_at"],
        )

    return await run_db(_insert)


async def update_member_role(
    session: AsyncSession,
    org_id: str,
    member_id: str,
    body: UpdateMemberRoleRequest,
) -> OrgMember:
    async def _update() -> OrgMember:
        current = await session.execute(
            text(
                """
                SELECT id::text AS id, email, role, clerk_user_id, created_at::text AS joined_at
                FROM org_members
                WHERE id = :member_id AND org_id = :org_id
                LIMIT 1
                """
            ),
            {"member_id": member_id, "org_id": org_id},
        )
        row = current.mappings().first()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "member not found"},
            )
        if row["role"] == "owner":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "cannot change the owner role"},
            )

        result = await session.execute(
            text(
                """
                UPDATE org_members
                SET role = :role
                WHERE id = :member_id AND org_id = :org_id
                RETURNING
                    id::text AS id,
                    email,
                    role,
                    clerk_user_id,
                    created_at::text AS joined_at
                """
            ),
            {"member_id": member_id, "org_id": org_id, "role": body.role},
        )
        updated = result.mappings().first()
        await session.commit()
        if updated is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "member not found"},
            )
        return OrgMember(
            id=updated["id"],
            email=updated["email"],
            role=updated["role"],
            clerk_user_id=updated["clerk_user_id"],
            joined_at=updated["joined_at"],
        )

    return await run_db(_update)


async def remove_member(session: AsyncSession, org_id: str, member_id: str) -> None:
    async def _delete() -> None:
        current = await session.execute(
            text(
                """
                SELECT role FROM org_members
                WHERE id = :member_id AND org_id = :org_id
                LIMIT 1
                """
            ),
            {"member_id": member_id, "org_id": org_id},
        )
        row = current.mappings().first()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "member not found"},
            )
        if row["role"] == "owner":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "cannot remove the organization owner"},
            )

        await session.execute(
            text(
                """
                DELETE FROM org_members
                WHERE id = :member_id AND org_id = :org_id
                """
            ),
            {"member_id": member_id, "org_id": org_id},
        )
        await session.commit()

    await run_db(_delete)


async def revoke_invite(session: AsyncSession, org_id: str, invite_id: str) -> None:
    async def _revoke() -> None:
        result = await session.execute(
            text(
                """
                UPDATE org_invites
                SET status = 'revoked'
                WHERE id = :invite_id
                  AND org_id = :org_id
                  AND status = 'pending'
                RETURNING id
                """
            ),
            {"invite_id": invite_id, "org_id": org_id},
        )
        if result.first() is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "invite not found"},
            )
        await session.commit()

    await run_db(_revoke)
