from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import AuthContext, require_authenticated_user, resolve_org_id
from api.db.postgres import get_session
from api.models import DeleteProjectRequest, ProjectSummary, UpdateProjectRequest
from api.services import projects as project_service

router = APIRouter(prefix="/v1/projects", tags=["projects"])


@router.patch("/{project_id}", response_model=ProjectSummary)
async def rename_project(
    project_id: str,
    body: UpdateProjectRequest,
    org_id: str = Depends(resolve_org_id),
    _: AuthContext = Depends(require_authenticated_user),
    session: AsyncSession = Depends(get_session),
) -> ProjectSummary:
    return await project_service.rename_project(session, org_id, project_id, body)


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_project(
    project_id: str,
    body: DeleteProjectRequest,
    org_id: str = Depends(resolve_org_id),
    _: AuthContext = Depends(require_authenticated_user),
    session: AsyncSession = Depends(get_session),
) -> Response:
    await project_service.delete_project(session, org_id, project_id, body)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
