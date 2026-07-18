from __future__ import annotations

from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.postgres import (
    get_session,
    lookup_org_id_for_api_key,
    lookup_org_id_for_clerk_org,
    lookup_org_id_for_clerk_user,
)
from shared.config import get_settings

_bearer_scheme = HTTPBearer(auto_error=False)
_jwk_client: PyJWKClient | None = None


@dataclass
class AuthContext:
    user_id: str | None
    org_id: str | None
    email: str | None = None
    clerk_org_id: str | None = None


def _clerk_auth_enabled() -> bool:
    return bool(get_settings().resolved_clerk_jwks_url())


def _get_jwk_client() -> PyJWKClient | None:
    global _jwk_client
    jwks_url = get_settings().resolved_clerk_jwks_url()
    if not jwks_url:
        return None
    if _jwk_client is None:
        _jwk_client = PyJWKClient(jwks_url)
    return _jwk_client


def _verify_clerk_token(token: str) -> dict:
    jwk_client = _get_jwk_client()
    if jwk_client is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail={"error": "unauthorized"}
        )

    try:
        signing_key = jwk_client.get_signing_key_from_jwt(token)
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            options={"verify_aud": False},
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "unauthorized"},
        ) from exc


def _extract_email(payload: dict) -> str | None:
    for key in ("email", "primary_email"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _is_api_key(token: str) -> bool:
    return token.startswith("ao_live_")


async def _auth_from_api_key(session: AsyncSession, token: str) -> AuthContext | None:
    if not _is_api_key(token):
        return None

    org_id = await lookup_org_id_for_api_key(session, token)
    if org_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail={"error": "invalid api key"}
        )

    return AuthContext(user_id=None, org_id=org_id, email=None)


async def get_auth_context(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    session: AsyncSession = Depends(get_session),
) -> AuthContext:
    settings = get_settings()

    if credentials is None or credentials.scheme.lower() != "bearer":
        if settings.environment == "development" and not _clerk_auth_enabled():
            return AuthContext(user_id=None, org_id=None, email=None)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail={"error": "unauthorized"}
        )

    api_key_auth = await _auth_from_api_key(session, credentials.credentials)
    if api_key_auth is not None:
        return api_key_auth

    if settings.environment == "development" and not _clerk_auth_enabled():
        return AuthContext(user_id="dev-user", org_id=None, email="dev@agentops.local")

    payload = _verify_clerk_token(credentials.credentials)
    user_id = payload.get("sub")
    clerk_org_id = payload.get("org_id")
    email = _extract_email(payload)

    if isinstance(clerk_org_id, str):
        org_id = await lookup_org_id_for_clerk_org(session, clerk_org_id)
        if org_id is None and user_id is not None:
            org_id = await lookup_org_id_for_clerk_user(session, user_id)
    elif user_id is not None:
        org_id = await lookup_org_id_for_clerk_user(session, user_id)
    else:
        org_id = None

    return AuthContext(
        user_id=user_id,
        org_id=org_id,
        email=email,
        clerk_org_id=clerk_org_id if isinstance(clerk_org_id, str) else None,
    )


async def require_authenticated_user(
    auth: AuthContext = Depends(get_auth_context),
) -> AuthContext:
    settings = get_settings()

    if settings.environment == "development" and not _clerk_auth_enabled():
        return AuthContext(user_id="dev-user", org_id=None, email="dev@agentops.local")

    if auth.user_id is None and auth.org_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail={"error": "unauthorized"}
        )

    return auth


async def resolve_org_id(
    org_id: str | None = Query(None, alias="org_id"),
    auth: AuthContext = Depends(get_auth_context),
) -> str:
    settings = get_settings()

    if settings.environment == "development" and not _clerk_auth_enabled():
        if org_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "org_id is required"},
            )
        return org_id

    if auth.org_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"error": "forbidden"})

    if org_id is not None and auth.org_id != org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"error": "forbidden"})

    return auth.org_id


async def get_optional_org_scope(
    auth: AuthContext = Depends(get_auth_context),
) -> str | None:
    settings = get_settings()
    if settings.environment == "development" and not _clerk_auth_enabled():
        return None
    return auth.org_id
