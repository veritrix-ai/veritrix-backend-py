from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from ingest.clickhouse import get_clickhouse_client
from ingest.postgres import dispose_engine
from ingest.routes.spans import router as spans_router
from shared.config import get_settings


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    clickhouse = get_clickhouse_client()
    try:
        await clickhouse.ensure_schema()
    except Exception:
        if settings.environment != "development":
            raise
    yield
    await dispose_engine()


app = FastAPI(title="AgentOps Ingest API", lifespan=lifespan)
app.include_router(spans_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.exception_handler(HTTPException)
async def http_exception_handler(_, exc: HTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(status_code=exc.status_code, content={"error": str(exc.detail)})


@app.exception_handler(ValueError)
async def value_error_handler(_, exc: ValueError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"error": str(exc)})


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    settings = get_settings()
    if settings.environment == "development":
        return JSONResponse(status_code=500, content={"error": str(exc)})
    return JSONResponse(status_code=500, content={"error": "internal server error"})
