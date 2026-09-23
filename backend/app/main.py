"""FastAPI entrypoint. `uvicorn app.main:app --reload` from /backend."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import auth, health, models, reports, scans
from app.core.config import settings
from app.core.logging import get_logger, setup_logging

setup_logging()
logger = get_logger(__name__)

DESCRIPTION = """
Backend for the Adversarial ML Red-Teaming Platform (M1-owned).

Upload a model, queue a scan, poll for a robustness scorecard and ATLAS-mapped findings.
The sandbox (M2), attack engine (M4) and ATLAS mapper (M3) are reached through fixed JSON
contracts documented in ARCHITECTURE.md; at Milestone 1 they are contract-shaped mocks.
"""

@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("api started", extra={"environment": settings.ENVIRONMENT})
    yield


app = FastAPI(
    lifespan=lifespan,
    title="Adversarial ML Red-Teaming Platform API",
    version="0.1.0",
    description=DESCRIPTION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Defaults to the Vite dev server; set CORS_ORIGINS in .env for a deployed frontend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(models.router)
app.include_router(scans.router)
app.include_router(reports.router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Log the stack trace, return a shaped error — never a raw traceback to the client."""
    logger.exception("unhandled error", extra={"path": request.url.path})
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "internal server error"},
    )
