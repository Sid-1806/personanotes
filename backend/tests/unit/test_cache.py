"""Unit tests for the in-memory cache/rate-limit backend and key helpers.

Drives the async backend via asyncio.run so no pytest-asyncio plugin is needed.
The Redis path is exercised only in integration; here we cover the fallback that
runs in dev and in CI.
"""

import asyncio

from app.core.cache import InMemoryBackend, prompt_cache_key


def _run(coro):
    return asyncio.run(coro)


# --- prompt key normalization --------------------------------------------

def test_prompt_key_is_normalized_and_stable():
    a = prompt_cache_key("  Explain   HNSW indexing  ")
    b = prompt_cache_key("explain hnsw indexing")
    assert a == b                      # whitespace + case normalized
    assert a != prompt_cache_key("explain hnsw")  # different prompt -> different key
    assert len(a) == 16


# --- cache get/set --------------------------------------------------------

def test_cache_miss_then_hit():
    backend = InMemoryBackend()

    async def scenario():
        assert await backend.get_json("k") is None          # miss
        await backend.set_json("k", {"notes": "hi"}, ttl=60)
        return await backend.get_json("k")

    assert _run(scenario()) == {"notes": "hi"}


def test_cache_respects_expiry():
    backend = InMemoryBackend()

    async def scenario():
        await backend.set_json("k", 1, ttl=0)  # ttl 0 -> no expiry stored
        assert await backend.get_json("k") == 1
        # Simulate an already-expired entry directly.
        backend._store["gone"] = (0.0, "old")  # expiry in the past
        return await backend.get_json("gone")

    assert _run(scenario()) is None


# --- fixed-window rate limiter -------------------------------------------

def test_fixed_window_counts_up_within_window():
    backend = InMemoryBackend()

    async def scenario():
        counts = []
        for _ in range(3):
            count, retry = await backend.incr_window("rl:gen:1", window=60)
            counts.append(count)
            assert retry >= 1
        return counts

    assert _run(scenario()) == [1, 2, 3]


def test_fixed_window_resets_after_expiry():
    backend = InMemoryBackend()

    async def scenario():
        await backend.incr_window("rl:gen:1", window=60)
        # Force the window to look elapsed, then the next call resets to 1.
        reset, count = backend._counters["rl:gen:1"]
        backend._counters["rl:gen:1"] = (0.0, count)  # reset time in the past
        count, _ = await backend.incr_window("rl:gen:1", window=60)
        return count

    assert _run(scenario()) == 1


def test_windows_are_isolated_per_key():
    backend = InMemoryBackend()

    async def scenario():
        await backend.incr_window("rl:gen:1", 60)
        await backend.incr_window("rl:gen:1", 60)
        other, _ = await backend.incr_window("rl:gen:2", 60)
        return other

    assert _run(scenario()) == 1  # a different user's counter starts fresh
