from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import setup_logging
from app.core.exceptions import AppError, app_error_handler, global_exception_handler
from app.api.routers import auth, users, lectures, notes, style, historical, dashboard

setup_logging()

app = FastAPI(
    title=settings.PROJECT_NAME, openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(Exception, global_exception_handler)

app.include_router(auth.router, prefix=settings.API_V1_STR, tags=["Authentication"])
app.include_router(users.router, prefix=f"{settings.API_V1_STR}/users", tags=["Users"])
app.include_router(
    lectures.router, prefix=f"{settings.API_V1_STR}/lectures", tags=["Lectures"]
)
app.include_router(notes.router, prefix=f"{settings.API_V1_STR}/notes", tags=["Notes"])
app.include_router(
    historical.router,
    prefix=f"{settings.API_V1_STR}/historical",
    tags=["Historical Notes"],
)
app.include_router(style.router, prefix=f"{settings.API_V1_STR}/style", tags=["Style"])
app.include_router(
    dashboard.router, prefix=f"{settings.API_V1_STR}/dashboard", tags=["Dashboard"]
)


@app.get("/")
def root():
    return {"message": "Welcome to the Personalized AI Notes Generator API"}
