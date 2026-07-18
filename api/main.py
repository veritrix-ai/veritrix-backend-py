from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.db.postgres import DatabaseUnavailableError, dispose_engine, is_db_connection_error
from api.routes.agents import router as agents_router
from api.routes.me import router as me_router
from api.routes.metrics import router as metrics_router
from api.routes.organization import router as organization_router
from api.routes.projects import router as projects_router
from api.routes.traces import router as traces_router
from shared.config import get_settings

logger = logging.getLogger("api")


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    if settings.environment != "development" and not settings.resolved_clerk_jwks_url():
        logger.error(
            "Clerk JWKS URL is not configured. Set CLERK_PUBLISHABLE_KEY "
            "(or CLERK_JWKS_URL) on this service — /v1/* requests will return 401."
        )
    yield
    await dispose_engine()


app = FastAPI(title="AgentOps App API", lifespan=lifespan)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.resolved_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(traces_router)
app.include_router(agents_router)
app.include_router(metrics_router)
app.include_router(me_router)
app.include_router(organization_router)
app.include_router(projects_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.exception_handler(HTTPException)
async def http_exception_handler(_, exc: HTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(status_code=exc.status_code, content={"error": str(exc.detail)})


async def database_unavailable_handler(_: Request, exc: Exception) -> JSONResponse:
    logger.error("Database unavailable: %s", exc)
    return JSONResponse(status_code=503, content={"error": "database unavailable"})


# Specific handlers avoid ServerErrorMiddleware re-raise + traceback spam.
app.add_exception_handler(DatabaseUnavailableError, database_unavailable_handler)
app.add_exception_handler(ConnectionRefusedError, database_unavailable_handler)
app.add_exception_handler(ConnectionResetError, database_unavailable_handler)
app.add_exception_handler(TimeoutError, database_unavailable_handler)


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    if is_db_connection_error(exc):
        return await database_unavailable_handler(_, exc)

    logger.exception("Unhandled API error: %s", exc)
    if settings.environment == "development":
        return JSONResponse(status_code=500, content={"error": str(exc)})
    return JSONResponse(status_code=500, content={"error": "internal server error"})
