import asyncio
import time
import requests

_cache = {}


async def cached_http_get(url, max_retries=3):
    if url in _cache:
        return _cache[url]

    def _inner():
        async def _fetch():
            last_err = None
            for attempt in range(max_retries):
                try:
                    resp = requests.get(url, timeout=10)
                    return resp.text
                except Exception as e:
                    last_err = e
                    time.sleep(0.1)
            raise last_err

        return asyncio.run(_fetch())

    result = _inner()
    _cache[url] = result
    return result


if __name__ == "__main__":
    out = asyncio.run(cached_http_get("https://example.com"))
    print(out[:200])
