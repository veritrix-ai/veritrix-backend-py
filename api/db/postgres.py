from __future__ import annotations

import logging
from collections.abc import AsyncGenerator, Awaitable, Callable
from typing import TypeVar

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, InterfaceError, OperationalError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from shared.config import get_settings

logger = logging.getLogger(__name__)

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None

T = TypeVar("T")


class DatabaseUnavailableError(Exception):
    """Raised when PostgreSQL cannot be reached."""


def is_db_connection_error(exc: BaseException | None) -> bool:
    if exc is None:
        return False
    if isinstance(exc, DatabaseUnavailableError):
        return True
    if isinstance(
        exc, (ConnectionRefusedError, ConnectionResetError, BrokenPipeError, TimeoutError)
    ):
        return True
    if isinstance(exc, OSError) and getattr(exc, "errno", None) in {61, 111, 10061}:
        return True
    if isinstance(exc, (OperationalError, InterfaceError, DBAPIError)):
        for candidate in (getattr(exc, "orig", None), exc.__cause__, exc.__context__):
            if (
                isinstance(candidate, BaseException)
                and candidate is not exc
                and is_db_connection_error(candidate)
            ):
                return True
        message = str(exc).lower()
        return any(
            token in message
            for token in (
                "connection refused",
                "could not connect",
                "connection reset",
                "server closed the connection",
                "timeout expired",
                "connect call failed",
                "name or service not known",
            )
        )

    cause = exc.__cause__ or exc.__context__
    if isinstance(cause, BaseException) and cause is not exc:
        return is_db_connection_error(cause)
    return False


async def run_db(operation: Callable[[], Awaitable[T]]) -> T:
    try:
        return await operation()
    except DatabaseUnavailableError:
        raise
    except Exception as exc:
        if is_db_connection_error(exc):
            logger.error("PostgreSQL connection failed: %s", exc)
            raise DatabaseUnavailableError("database unavailable") from exc
        raise


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = create_async_engine(get_settings().database_url, pool_pre_ping=True)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _session_factory


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    session_factory = get_session_factory()
    async with session_factory() as session:
        yield session


async def lookup_org_id_for_clerk_user(session: AsyncSession, clerk_user_id: str) -> str | None:
    async def _lookup() -> str | None:
        result = await session.execute(
            text("""
                SELECT org_id::text
                FROM users
                WHERE clerk_user_id = :clerk_user_id
                LIMIT 1
                """),
            {"clerk_user_id": clerk_user_id},
        )
        row = result.first()
        return row[0] if row else None

    return await run_db(_lookup)


async def lookup_org_id_for_clerk_org(session: AsyncSession, clerk_org_id: str) -> str | None:
    async def _lookup() -> str | None:
        result = await session.execute(
            text("""
                SELECT id::text
                FROM orgs
                WHERE clerk_org_id = :clerk_org_id
                LIMIT 1
                """),
            {"clerk_org_id": clerk_org_id},
        )
        row = result.first()
        return row[0] if row else None

    return await run_db(_lookup)


async def lookup_org_id_for_api_key(session: AsyncSession, api_key: str) -> str | None:
    async def _lookup() -> str | None:
        result = await session.execute(
            text("""
                SELECT org_id::text
                FROM api_keys
                WHERE key_value = :api_key
                  AND revoked_at IS NULL
                LIMIT 1
                """),
            {"api_key": api_key},
        )
        row = result.first()
        return row[0] if row else None

    return await run_db(_lookup)


async def dispose_engine() -> None:
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None
