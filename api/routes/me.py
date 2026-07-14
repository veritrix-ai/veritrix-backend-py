from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import AuthContext, require_authenticated_user
from api.db.postgres import get_session
from api.models import MeResponse, OnboardingRequest
from api.services.onboarding import get_user_profile, provision_user

router = APIRouter(tags=["account"])


def _resolve_email(auth: AuthContext, request: OnboardingRequest | None = None) -> str:
    if auth.email:
        return auth.email
    if request and request.email:
        return request.email.strip()
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={"error": "email is required"},
    )


@router.get("/v1/me", response_model=MeResponse)
async def get_me(
    auth: AuthContext = Depends(require_authenticated_user),
    session: AsyncSession = Depends(get_session),
) -> MeResponse:
    profile = await get_user_profile(session, auth.user_id)  # type: ignore[arg-type]
    if profile is None:
        return MeResponse(
            clerk_user_id=auth.user_id,  # type: ignore[arg-type]
            email=auth.email or "",
            provisioned=False,
        )
    return profile


@router.post("/v1/onboarding", response_model=MeResponse, status_code=status.HTTP_201_CREATED)
async def create_onboarding(
    body: OnboardingRequest,
    auth: AuthContext = Depends(require_authenticated_user),
    session: AsyncSession = Depends(get_session),
) -> MeResponse:
    email = _resolve_email(auth, body)
    return await provision_user(
        session,
        clerk_user_id=auth.user_id,  # type: ignore[arg-type]
        email=email,
        request=body,
    )
