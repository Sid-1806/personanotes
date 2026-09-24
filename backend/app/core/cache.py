"""Cache + rate-limit backend with graceful degradation.

A tiny async interface (``get_json`` / ``set_json`` / ``incr_window``) backed by
Redis when ``REDIS_URL`` is configured and reachable, and by an in-process store
otherwise. This lets the app run locally with no extra infrastructure while
using Redis in production (shared across workers). All Redis failures degrade
safely: cache reads miss, cache writes no-op, and the rate limiter fails *open*.
"""

import asyncio
import hashlib
import json
import logging
import time
from typing import Any, Optional, Tuple

from app.core.config import settings

logger = logging.getLogger(__name__)


def prompt_cache_key(prompt: str) -> str:
    """Stable short hash of a prompt, normalized for whitespace/case."""
    normalized = " ".join((prompt or "").strip().lower().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


class InMemoryBackend:
    """Process-local fallback. Fine for single-worker/dev; not shared across pods."""

    def __init__(self) -> None:
        self._store: dict[str, Tuple[Optional[float], Any]] = {}
        self._counters: dict[str, Tuple[float, int]] = {}
        self._lock = asyncio.Lock()

    async def get_json(self, key: str) -> Optional[Any]:
        async with self._lock:
            item = self._store.get(key)
            if not item:
                return None
            expiry, value = item
            if expiry is not None and expiry < time.time():
                self._store.pop(key, None)
                return None
            return value

    async def set_json(self, key: str, value: Any, ttl: int) -> None:
        async with self._lock:
            self._store[key] = (time.time() + ttl if ttl else None, value)

    async def incr_window(self, key: str, window: int) -> Tuple[int, int]:
        """Fixed-window counter. Returns (count_in_window, seconds_until_reset)."""
        async with self._lock:
            now = time.time()
            reset, count = self._counters.get(key, (now + window, 0))
            if reset < now:  # window elapsed -> start a new one
                reset, count = now + window, 0
            count += 1
            self._counters[key] = (reset, count)
            return count, max(1, int(reset - now))


class RedisBackend:
    """Shared backend for multi-worker deployments."""

    def __init__(self, client: Any) -> None:
        self._r = client

    async def get_json(self, key: str) -> Optional[Any]:
        try:
            raw = await self._r.get(key)
            return json.loads(raw) if raw else None
        except Exception as exc:  # never let cache issues break a request
            logger.warning("cache get failed (%s); treating as miss", exc)
            return None

    async def set_json(self, key: str, value: Any, ttl: int) -> None:
        try:
            await self._r.set(key, json.dumps(value), ex=ttl or None)
        except Exception as exc:
            logger.warning("cache set failed (%s); skipping", exc)

    async def incr_window(self, key: str, window: int) -> Tuple[int, int]:
        try:
            count = await self._r.incr(key)
            if count == 1:
                await self._r.expire(key, window)
            ttl = await self._r.ttl(key)
            return int(count), ttl if ttl and ttl > 0 else window
        except Exception as exc:  # fail open so a Redis outage can't lock everyone out
            logger.warning("rate-limit backend failed (%s); allowing request", exc)
            return 0, window


_backend: Optional[Any] = None
_init_lock = asyncio.Lock()


async def get_cache() -> Any:
    """Return the shared backend, initializing (and probing Redis) once."""
    global _backend
    if _backend is not None:
        return _backend
    async with _init_lock:
        if _backend is not None:
            return _backend
        if settings.REDIS_URL:
            try:
                import redis.asyncio as aioredis

                client = aioredis.from_url(
                    settings.REDIS_URL, decode_responses=True
                )
                await client.ping()
                _backend = RedisBackend(client)
                logger.info("Cache/rate-limit backend: Redis")
            except Exception as exc:
                logger.warning(
                    "Redis unavailable (%s); using in-memory backend", exc
                )
                _backend = InMemoryBackend()
        else:
            _backend = InMemoryBackend()
            logger.info("Cache/rate-limit backend: in-memory")
    return _backend


def reset_cache_for_tests() -> None:
    """Test hook: drop the singleton so each test gets a fresh backend."""
    global _backend
    _backend = None
