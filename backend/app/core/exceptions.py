from fastapi import Request, status
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)


class AppError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code


class LLMServiceError(AppError):
    def __init__(
        self, message: str = "AI Service is currently unavailable. Please try again."
    ):
        super().__init__(message, status_code=status.HTTP_503_SERVICE_UNAVAILABLE)


class FileProcessingError(AppError):
    def __init__(self, message: str = "Failed to process the uploaded file."):
        super().__init__(message, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)


async def app_error_handler(request: Request, exc: AppError):
    logger.error(f"AppError: {exc.message} on path {request.url.path}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message},
    )


async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled Exception on {request.url.path}: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": f"An unexpected error occurred: {str(exc)}"},
    )
