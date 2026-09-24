"""Per-user rate limiting as a FastAPI dependency.

Fixed-window counter keyed by user id, backed by the shared cache backend
(Redis in production, in-memory otherwise). Applied to the LLM endpoints, where
Gemini calls are the real cost/latency bottleneck.
"""

import logging

from fastapi import Depends, HTTPException, status

from app.api import deps
from app.core.cache import get_cache
from app.core.config import settings
from app.models.user import User

logger = logging.getLogger(__name__)


def rate_limit(scope: str, limit: int, window: int):
    """Build a dependency that allows at most `limit` calls per `window` seconds."""

    async def _dependency(current_user: User = Depends(deps.get_current_user)) -> None:
        if not settings.RATE_LIMIT_ENABLED:
            return
        backend = await get_cache()
        key = f"rl:{scope}:{current_user.id}"
        count, retry_after = await backend.incr_window(key, window)
        if count > limit:
            logger.info("rate limit hit: user=%s scope=%s", current_user.id, scope)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded for {scope}. Retry in {retry_after}s.",
                headers={"Retry-After": str(retry_after)},
            )

    return _dependency
