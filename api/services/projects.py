from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.postgres import run_db
from api.models import DeleteProjectRequest, ProjectSummary, UpdateProjectRequest


async def rename_project(
    session: AsyncSession,
    org_id: str,
    project_id: str,
    body: UpdateProjectRequest,
) -> ProjectSummary:
    async def _rename() -> ProjectSummary:
        result = await session.execute(
            text("""
                UPDATE projects
                SET name = :name
                WHERE id = :project_id AND org_id = :org_id
                RETURNING id::text AS id, name
                """),
            {
                "project_id": project_id,
                "org_id": org_id,
                "name": body.name.strip(),
            },
        )
        row = result.mappings().first()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "project not found"},
            )
        await session.commit()
        return ProjectSummary(id=row["id"], name=row["name"])

    return await run_db(_rename)


async def delete_project(
    session: AsyncSession,
    org_id: str,
    project_id: str,
    body: DeleteProjectRequest,
) -> None:
    async def _delete() -> None:
        existing = await session.execute(
            text("""
                SELECT p.name
                FROM projects p
                WHERE p.id = :project_id AND p.org_id = :org_id
                LIMIT 1
                """),
            {"project_id": project_id, "org_id": org_id},
        )
        project = existing.mappings().first()
        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "project not found"},
            )
        if body.confirm_name != project["name"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "project name confirmation does not match"},
            )
        # Preserve traces, but revoke keys so the deleted project cannot ingest new spans.
        await session.execute(
            text("""
                UPDATE api_keys
                SET revoked_at = COALESCE(revoked_at, now()),
                    project_id = NULL
                WHERE project_id = :project_id AND org_id = :org_id
                """),
            {"project_id": project_id, "org_id": org_id},
        )
        await session.execute(
            text("""
                DELETE FROM projects
                WHERE id = :project_id AND org_id = :org_id
                """),
            {"project_id": project_id, "org_id": org_id},
        )
        await session.commit()

    await run_db(_delete)
