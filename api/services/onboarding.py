from __future__ import annotations

import secrets
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.postgres import run_db
from api.models import ApiKeySummary, MeResponse, OnboardingRequest, ProjectSummary


async def get_user_profile(session: AsyncSession, clerk_user_id: str) -> MeResponse | None:
    async def _load() -> MeResponse | None:
        result = await session.execute(
            text("""
                SELECT
                    u.clerk_user_id,
                    u.email,
                    o.id::text AS org_id,
                    o.clerk_org_id,
                    o.name AS org_name
                FROM users u
                JOIN orgs o ON o.id = u.org_id
                WHERE u.clerk_user_id = :clerk_user_id
                LIMIT 1
                """),
            {"clerk_user_id": clerk_user_id},
        )
        row = result.mappings().first()
        if row is None:
            return None

        org_id = row["org_id"]
        projects = await _list_projects(session, org_id)
        api_keys = await _list_api_keys(session, org_id)

        return MeResponse(
            clerk_user_id=row["clerk_user_id"],
            email=row["email"],
            org_id=org_id,
            clerk_org_id=row.get("clerk_org_id"),
            org_name=row["org_name"],
            projects=projects,
            api_keys=api_keys,
            provisioned=True,
        )

    return await run_db(_load)


async def provision_user(
    session: AsyncSession,
    *,
    clerk_user_id: str,
    email: str,
    request: OnboardingRequest,
) -> MeResponse:
    existing = await get_user_profile(session, clerk_user_id)
    if existing is not None:
        return existing

    org_id = str(uuid.uuid4())
    project_id = str(uuid.uuid4())
    org_name = request.org_name.strip()
    api_key_value = f"ao_live_{secrets.token_hex(24)}"

    async def _insert() -> None:
        await session.execute(
            text("""
                INSERT INTO orgs (id, name, clerk_org_id)
                VALUES (:id, :name, :clerk_org_id)
                """),
            {
                "id": org_id,
                "name": org_name,
                "clerk_org_id": request.clerk_org_id,
            },
        )
        await session.execute(
            text("""
                INSERT INTO users (org_id, clerk_user_id, email)
                VALUES (:org_id, :clerk_user_id, :email)
                RETURNING id::text
                """),
            {"org_id": org_id, "clerk_user_id": clerk_user_id, "email": email},
        )
        user_row = (
            await session.execute(
                text("""
                    SELECT id::text
                    FROM users
                    WHERE clerk_user_id = :clerk_user_id
                    LIMIT 1
                    """),
                {"clerk_user_id": clerk_user_id},
            )
        ).first()
        user_id = user_row[0] if user_row else None
        if user_id is None:
            raise RuntimeError("Failed to create onboarding user")
        await session.execute(
            text("""
                INSERT INTO onboarding_profiles (
                    user_id,
                    org_id,
                    usage,
                    company_size,
                    building_description,
                    stage,
                    heard_from,
                    frameworks,
                    providers,
                    help_goals
                )
                VALUES (
                    :user_id,
                    :org_id,
                    :usage,
                    :company_size,
                    :building_description,
                    :stage,
                    :heard_from,
                    :frameworks,
                    :providers,
                    :help_goals
                )
                """),
            {
                "user_id": user_id,
                "org_id": org_id,
                "usage": request.usage,
                "company_size": request.company_size,
                "building_description": request.building_description,
                "stage": request.stage,
                "heard_from": request.heard_from,
                "frameworks": request.frameworks,
                "providers": request.providers,
                "help_goals": request.help_goals,
            },
        )
        await session.execute(
            text("""
                INSERT INTO org_members (org_id, user_id, clerk_user_id, email, role)
                VALUES (:org_id, :user_id, :clerk_user_id, :email, 'owner')
                ON CONFLICT (org_id, email) DO NOTHING
                """),
            {
                "org_id": org_id,
                "user_id": user_id,
                "clerk_user_id": clerk_user_id,
                "email": email,
            },
        )
        await session.execute(
            text("""
                INSERT INTO projects (id, org_id, name)
                VALUES (:id, :org_id, :name)
                """),
            {"id": project_id, "org_id": org_id, "name": "Default Project"},
        )
        await session.execute(
            text("""
                INSERT INTO api_keys (org_id, project_id, key_value, name)
                VALUES (:org_id, :project_id, :key_value, :name)
                """),
            {
                "org_id": org_id,
                "project_id": project_id,
                "key_value": api_key_value,
                "name": "Default Key",
            },
        )
        await session.commit()

    await run_db(_insert)

    profile = await get_user_profile(session, clerk_user_id)
    if profile is None:
        raise RuntimeError("Failed to load provisioned user profile")
    return profile


async def _list_projects(session: AsyncSession, org_id: str) -> list[ProjectSummary]:
    result = await session.execute(
        text("""
            SELECT id::text AS id, name
            FROM projects
            WHERE org_id = :org_id
            ORDER BY created_at ASC
            """),
        {"org_id": org_id},
    )
    return [ProjectSummary(id=row["id"], name=row["name"]) for row in result.mappings()]


async def _list_api_keys(session: AsyncSession, org_id: str) -> list[ApiKeySummary]:
    result = await session.execute(
        text("""
            SELECT
                ak.id::text AS id,
                ak.key_value,
                ak.name,
                p.name AS project_name
            FROM api_keys ak
            LEFT JOIN projects p ON p.id = ak.project_id
            WHERE ak.org_id = :org_id
              AND ak.revoked_at IS NULL
            ORDER BY ak.created_at ASC
            """),
        {"org_id": org_id},
    )
    return [
        ApiKeySummary(
            id=row["id"],
            key_value=row["key_value"],
            name=row["name"],
            project_name=row["project_name"] or "Default Project",
        )
        for row in result.mappings()
    ]
