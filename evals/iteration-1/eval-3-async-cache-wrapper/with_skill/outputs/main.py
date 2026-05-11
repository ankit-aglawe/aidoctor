"""Async HTTP fetch with in-memory caching and bounded retry/backoff.

Notes on deviations from the original request:
- The task asked for `requests.get` inside an async function. `requests` is
  synchronous and would block the event loop, so we use `httpx.AsyncClient`.
- The task asked for `time.sleep(0.1)` between retries. Inside an async
  function this also blocks the loop, so we use `await asyncio.sleep(0.1)`.
- The task asked us to call `asyncio.run` on an inner coroutine. Calling
  `asyncio.run` from inside a running event loop raises RuntimeError, so we
  `await` the coroutine directly. `asyncio.run` is reserved for the
  top-level entry point in `__main__`.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Final

import httpx

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT_SECONDS: Final[float] = 10.0
_RETRY_DELAY_SECONDS: Final[float] = 0.1
_MAX_ATTEMPTS: Final[int] = 3

_cache: dict[str, str] = {}
_cache_lock = asyncio.Lock()


async def cached_get(
    url: str,
    *,
    timeout: float = _DEFAULT_TIMEOUT_SECONDS,
    max_attempts: int = _MAX_ATTEMPTS,
) -> str:
    """Fetch `url` over HTTP, caching the response body by URL.

    Retries transient network failures up to `max_attempts` times with a
    fixed 100ms async sleep between attempts. The cache is process-local
    and unbounded by design; wrap with an LRU policy if you need eviction.
    """
    async with _cache_lock:
        hit = _cache.get(url)
    if hit is not None:
        return hit

    body = await _fetch_with_retries(url, timeout=timeout, max_attempts=max_attempts)

    async with _cache_lock:
        # Another coroutine may have populated the cache while we fetched;
        # prefer the first write so callers see a stable value.
        return _cache.setdefault(url, body)


async def _fetch_with_retries(
    url: str,
    *,
    timeout: float,
    max_attempts: int,
) -> str:
    last_exc: httpx.HTTPError | None = None
    async with httpx.AsyncClient(timeout=timeout) as client:
        for attempt in range(1, max_attempts + 1):
            try:
                response = await client.get(url)
                response.raise_for_status()
                return response.text
            except httpx.HTTPError as exc:
                last_exc = exc
                logger.warning(
                    "cached_get attempt %d/%d for %s failed: %s",
                    attempt,
                    max_attempts,
                    url,
                    exc,
                )
                if attempt == max_attempts:
                    break
                await asyncio.sleep(_RETRY_DELAY_SECONDS)
    assert last_exc is not None  # loop exits only via return or after setting last_exc
    raise last_exc


async def _main() -> None:
    body = await cached_get("https://example.com")
    logger.info("fetched %d bytes", len(body))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(_main())
