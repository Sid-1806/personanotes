import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import (
    auth,
    chat,
    courses,
    dashboard,
    historical,
    lectures,
    notes,
    search,
    style,
    users,
)
from app.core.config import settings
from app.core.exceptions import AppError, app_error_handler, global_exception_handler
from app.core.logging import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup housekeeping.

    In-process ingestion does not survive a restart, and hosts restart
    containers routinely. Sweeping anything left mid-flight turns a permanent
    spinner into a failure the user can actually retry.
    """
    try:
        from app.services.ingestion import requeue_stuck_lectures

        reset = requeue_stuck_lectures()
        if reset:
            logger.info("Marked %s interrupted ingestion(s) as retryable", reset)
    except Exception as exc:  # never block startup on housekeeping
        logger.warning("Startup ingestion sweep skipped: %s", exc)
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    # The client reads Retry-After to show a real countdown on a rate limit
    # rather than a generic failure.
    expose_headers=["Retry-After"],
)

app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(Exception, global_exception_handler)

V1 = settings.API_V1_STR

app.include_router(auth.router, prefix=V1, tags=["Authentication"])
app.include_router(users.router, prefix=f"{V1}/users", tags=["Users"])
app.include_router(courses.router, prefix=f"{V1}/courses", tags=["Courses"])
app.include_router(lectures.router, prefix=f"{V1}/lectures", tags=["Lectures"])
app.include_router(notes.router, prefix=f"{V1}/notes", tags=["Notes"])
app.include_router(search.router, prefix=f"{V1}/search", tags=["Search"])
app.include_router(chat.router, prefix=f"{V1}/chat", tags=["Chat"])
app.include_router(historical.router, prefix=f"{V1}/historical", tags=["Historical Notes"])
app.include_router(style.router, prefix=f"{V1}/style", tags=["Style"])
app.include_router(dashboard.router, prefix=f"{V1}/dashboard", tags=["Dashboard"])


@app.get("/")
def root():
    return {"message": "Welcome to the Personalized AI Notes Generator API"}


@app.get("/health")
def health():
    """Liveness probe for the deployment platform."""
    return {"status": "ok"}
