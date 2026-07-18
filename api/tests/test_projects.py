from __future__ import annotations

import pytest
from fastapi import HTTPException

from api.models import DeleteProjectRequest
from api.services import projects as project_service


class ProjectSession:
    def __init__(self, name: str = "Default Project") -> None:
        self.name = name
        self.committed = False
        self.statements: list[str] = []

    async def execute(self, query: object, _params: object = None) -> object:
        sql = str(query)
        self.statements.append(sql)
        project = {"name": self.name}

        class Result:
            def mappings(self) -> Result:
                return self

            def first(self) -> dict[str, object]:
                return project

        return Result()

    async def commit(self) -> None:
        self.committed = True


@pytest.mark.asyncio
async def test_delete_project_revokes_keys_and_preserves_traces() -> None:
    session = ProjectSession()

    await project_service.delete_project(
        session,  # type: ignore[arg-type] - focused SQLAlchemy session test double
        "org-1",
        "project-1",
        DeleteProjectRequest(confirm_name="Default Project"),
    )

    assert any("UPDATE api_keys" in sql for sql in session.statements)
    assert any("DELETE FROM projects" in sql for sql in session.statements)
    assert all("ALTER TABLE" not in sql for sql in session.statements)
    assert session.committed is True


@pytest.mark.asyncio
async def test_delete_project_rejects_wrong_confirmation() -> None:
    session = ProjectSession()

    with pytest.raises(HTTPException) as exc_info:
        await project_service.delete_project(
            session,  # type: ignore[arg-type] - focused SQLAlchemy session test double
            "org-1",
            "project-1",
            DeleteProjectRequest(confirm_name="Wrong name"),
        )

    assert exc_info.value.status_code == 400
    assert session.committed is False
