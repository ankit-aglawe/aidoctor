# /aidoctor:simplify — eval-3 async-cache-wrapper baseline review

## Phase 1 — Identified changes

```python
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
```

(Entire file — 33 lines including trailing newline. Treated as a fresh just-written diff.)

## Phase 2 — Three-angle findings

### Reviewer 1: Code Reuse
- **Hand-rolled retry loop (lines 14–22)** duplicates functionality already available in well-known libraries. `urllib3.util.Retry` + `requests.adapters.HTTPAdapter` (already a transitive dep via `requests`) covers retries with backoff; `tenacity` (`@retry(stop=stop_after_attempt, wait=wait_fixed)`) is the canonical reuse target if `tenacity` is acceptable. The custom `last_err` accumulator is reinventing what those utilities ship.
- **Hand-rolled in-memory cache (`_cache = {}` at line 5)** duplicates `functools.lru_cache` / `functools.cache`. For an async function the reuse target is `async_lru.alru_cache` or `cachetools`. The module-level dict has no eviction, no size cap, no TTL, no thread-safety — all solved by stdlib/PyPI primitives.
- **Sync HTTP client (`requests` on line 3, called at line 17)** duplicates async-native clients already idiomatic in an `async def` context: `httpx.AsyncClient` (drop-in API surface) or `aiohttp.ClientSession`. Picking `requests` inside `async def` means we cannot reuse the event-loop concurrency the caller already paid for.
- **Module-level mutable singleton (`_cache`)** — no reuse of a `Cache` class boundary means every test that imports this module shares state. A `functools.cache`-decorated function would localize state per-decorated-callable and give a `.cache_clear()` method for free.

### Reviewer 2: Code Quality
- **🚨 HEADLINE: async/sync mismatch — `cached_http_get` is declared `async def` but does zero awaiting and performs only blocking work.** Lines 12–26 wrap blocking `requests.get` + `time.sleep` in a *nested* `async def _fetch()` that is then run via `asyncio.run(_fetch())` from *inside* `_inner()`, which itself is called synchronously from the outer `async def`. Net effect: the outer coroutine blocks the caller's event loop for the entire HTTP request (and retries), and `asyncio.run` is invoked from a context that may already have a running loop — which raises `RuntimeError: asyncio.run() cannot be called from a running event loop`. This function is broken in any real async caller. The `async def` is a lie: there is no `await` anywhere in the body.
- **🚨 Nested `asyncio.run` inside another `asyncio.run` (lines 24 + 32).** `main` block calls `asyncio.run(cached_http_get(...))`, which awaits a coroutine whose body synchronously calls `asyncio.run(_fetch())`. Python's docs explicitly forbid this: "This function cannot be called when another asyncio event loop is running in the same thread." It will raise at runtime. The script only "works" by accident because the outer `asyncio.run` finishes setting up the loop, then the inner `_inner()` is invoked from coroutine body before any `await` yields — but the inner `asyncio.run` still detects the running loop and raises.
- **Pointless inner-function ladder (`_inner` → `_fetch`)** — two layers of nested closures to do one HTTP GET with retries. There is no reason for `_inner` to exist; `_fetch` does not need to be `async`. Flatten to a single retry loop.
- **`except Exception as e`** at line 19 is overly broad — swallows `KeyboardInterrupt`'s parent class siblings (well, not Interrupt itself, but `SystemExit` etc. are caught by bare except not Exception, so this part is OK) but more importantly catches programming errors (`AttributeError`, `TypeError`) that should crash. Should narrow to `requests.RequestException`.
- **Unused loop variable `attempt`** at line 15 — rename to `_` to signal intent, or use it for exponential backoff.
- **`last_err = None` then unconditional `raise last_err`** (line 22) — if `max_retries=0` is ever passed, the `for` loop body never runs and `raise None` is a `TypeError`. Guard with `raise last_err or RuntimeError("no attempts made")` or validate input.
- **Module-level mutable global `_cache`** — leading underscore says "private" but it's still global mutable state with no locking. In an async context across tasks, two coroutines could race on the `if url in _cache` check (admittedly low-stakes for a dict, but still poor form).
- **`time.sleep(0.1)`** at line 21 — synchronous sleep inside an `async def` (via the inner sync wrapper) blocks the event loop. Should be `await asyncio.sleep(0.1)` in an actual async retry loop.
- **No type hints** anywhere — `url: str`, `max_retries: int`, return `-> str`. Project rules and `aidoctor` flag missing annotations on public functions.
- **No docstring** on `cached_http_get` — public-ish function with non-obvious caching + retry behavior.
- **`requests.get(..., timeout=10)`** — magic number 10 should be a named constant or parameter.
- **`if __name__ == "__main__":` block prints `out[:200]`** with no guard that `out` is non-None / is a string — fine for a demo but worth a comment.
- Likely `aidoctor` rule hits: `async-without-await`, `asyncio-run-in-coroutine`, `blocking-call-in-async`, `bare-except-too-broad`, `missing-type-hints`, `missing-docstring`, `mutable-module-global`.

### Reviewer 3: Efficiency
- **Event-loop starvation (lines 17, 21):** `requests.get` (blocking socket I/O) and `time.sleep(0.1)` block the entire event loop for the duration of every request + retry. In any real async app this serializes every "concurrent" caller — the supposed concurrency benefit of `async def` is fully lost. `httpx.AsyncClient.get` + `asyncio.sleep` would let the loop do useful work during the round-trip.
- **Cache stores only successful results, but failures cost full retry budget every call (no negative caching).** If `example.com` is down, every caller pays `max_retries * (timeout + sleep)` again. Either cache short-lived failures or cache the in-flight `asyncio.Task` so concurrent callers share one request (thundering-herd fix).
- **Thundering herd / duplicate in-flight requests:** Two near-simultaneous calls for the same URL both miss the cache and both fire HTTP requests. Storing a `Future`/`Task` in `_cache` instead of the result deduplicates in-flight fetches.
- **Constant retry backoff (`time.sleep(0.1)`)** — no exponential growth, no jitter. Aggressive retries against a struggling upstream make things worse. `0.1 * (2 ** attempt)` + jitter is the standard.
- **Unbounded cache growth:** `_cache` grows forever as new URLs are seen. For a long-running process this is a memory leak. `functools.lru_cache(maxsize=...)` or `cachetools.TTLCache` bounds it.
- **No connection pooling reuse:** every call creates a new `requests` session implicitly. Reusing a `requests.Session()` (or `httpx.AsyncClient` instance) keeps TCP + TLS connections warm — significant per-request savings on HTTPS.
- **`asyncio.run` per call (line 24):** spinning up and tearing down an event loop on every retry block is enormously wasteful — even if the function were rewritten to be properly async, `asyncio.run` should be called at most once per program (or per top-level entry).
- **Reads full response body via `resp.text` (line 18)** regardless of size — fine for `example.com` but for a general utility this is unbounded memory per cached entry.

### Phase 2 → Phase 3 transition
Phase 2 complete. Reuse: 4 findings. Quality: 12 findings. Efficiency: 8 findings. Total unique: ~18 (significant overlap — async/sync mismatch surfaced by all three reviewers; cache-without-bound surfaced by reuse + efficiency; sync HTTP client surfaced by reuse + quality + efficiency). Beginning decision brief.

## Phase 3 — Decision brief

```
D1 — Which findings should I fix?
ELI10: All three reviewers agree the file is broken, not just untidy. The headline
is that `cached_http_get` is declared `async` but never awaits anything — and it
calls `asyncio.run(_fetch())` from inside its own body, which Python forbids
when an event loop is already running (and the `__main__` block guarantees one
is). This file will raise RuntimeError on first real use. Three reviewers
independently flagged the async/sync mismatch and the nested `asyncio.run`, so
those are not taste calls. The reuse + efficiency findings (httpx, alru_cache,
exponential backoff, in-flight dedup) are the "and while we're here" wins.

Recommendation: B — rewrite the function properly. This is not a "fix two lints"
situation; the function does not work. A surgical patch (option A) leaves a
broken-by-design contract: an `async def` that blocks the loop on every call.

A) Minimal correctness fix — drop the `async def`, drop the inner `asyncio.run`,
   keep `requests` + module-level dict. ~5 line diff.
  ✅ Smallest possible change; preserves call sites that import the name.
  ❌ Caller's `asyncio.run(cached_http_get(...))` at line 32 still works only
     because the function is a coroutine; if we make it sync, the call site
     must change too. AND we leave a blocking I/O function pretending it lives
     in an async codebase.

B) Proper async rewrite — `httpx.AsyncClient`, `await asyncio.sleep`, in-flight
   dedup via cached `asyncio.Task`, bounded cache, exponential backoff with
   jitter, type hints, docstring. (recommended)
  ✅ Function actually works as advertised; event loop is not blocked;
     concurrent callers for the same URL share one request; cache is bounded.
  ❌ Bigger diff; adds `httpx` dependency (or commits to `aiohttp`).

C) Show me the finding list, I'll pick.
  ✅ Full control.
  ❌ Slower; the headline bug needs B-shaped surgery anyway.

Net: B. The file is currently broken at runtime — A papers over that, and the
reuse/efficiency wins (httpx pool reuse, in-flight dedup, bounded cache, proper
backoff) come essentially for free once we're already touching the function.
```

## Phase 4 — If user accepts your recommendation (B — proper async rewrite)

### Edit 1 — Replace imports (lines 1–3)

**Old (lines 1–3):**
```python
import asyncio
import time
import requests
```

**New:**
```python
import asyncio
import random
from typing import Awaitable

import httpx
```

Rationale: `time` and `requests` are gone (no blocking I/O in an async function). `random` for jitter. `httpx` for an async-native client. `Awaitable` for the in-flight-task cache type hint.

### Edit 2 — Replace cache + function body (lines 5–28)

**Old (lines 5–28):**
```python
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
```

**New:**
```python
_REQUEST_TIMEOUT_S = 10.0
_BACKOFF_BASE_S = 0.1
_CACHE_MAX_ENTRIES = 1024

# Stores completed responses *and* in-flight asyncio.Tasks so that concurrent
# callers for the same URL share a single HTTP request (thundering-herd guard).
_cache: dict[str, Awaitable[str] | str] = {}
_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=_REQUEST_TIMEOUT_S)
    return _client


async def _fetch_with_retry(url: str, max_retries: int) -> str:
    """GET `url`, retrying transient failures with exponential backoff + jitter."""
    if max_retries < 1:
        raise ValueError("max_retries must be >= 1")
    last_err: Exception | None = None
    client = _get_client()
    for attempt in range(max_retries):
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.text
        except httpx.HTTPError as e:
            last_err = e
            if attempt < max_retries - 1:
                delay = _BACKOFF_BASE_S * (2 ** attempt) + random.uniform(0, _BACKOFF_BASE_S)
                await asyncio.sleep(delay)
    assert last_err is not None  # loop ran >=1 time, so this was set
    raise last_err


async def cached_http_get(url: str, max_retries: int = 3) -> str:
    """Async GET with in-memory caching and in-flight request deduplication.

    Successful responses are cached by URL. Concurrent callers requesting the
    same URL share one underlying HTTP request via a cached `asyncio.Task`.
    """
    cached = _cache.get(url)
    if isinstance(cached, str):
        return cached
    if cached is not None:  # in-flight Task
        return await cached  # type: ignore[no-any-return]

    if len(_cache) >= _CACHE_MAX_ENTRIES:
        # crude FIFO eviction — swap for cachetools.LRUCache if hot-path matters
        _cache.pop(next(iter(_cache)))

    task = asyncio.create_task(_fetch_with_retry(url, max_retries))
    _cache[url] = task
    try:
        result = await task
    except Exception:
        _cache.pop(url, None)  # don't pin a failed task
        raise
    _cache[url] = result
    return result
```

### Edit 3 — `__main__` block (lines 31–33)

**Old (lines 31–33):**
```python
if __name__ == "__main__":
    out = asyncio.run(cached_http_get("https://example.com"))
    print(out[:200])
```

**New:**
```python
async def _main() -> None:
    try:
        out = await cached_http_get("https://example.com")
        print(out[:200])
    finally:
        if _client is not None:
            await _client.aclose()


if __name__ == "__main__":
    asyncio.run(_main())
```

Rationale: `asyncio.run` is now called exactly once at the top level. The function is awaited, not nested-run. The shared `httpx.AsyncClient` is closed cleanly.

### Post-fix verification checklist
- [ ] `python -c "import asyncio; from main import cached_http_get; asyncio.run(cached_http_get('https://example.com'))"` no longer raises `RuntimeError: asyncio.run() cannot be called from a running event loop`.
- [ ] `aidoctor scan main.py` — expect `async-without-await`, `asyncio-run-in-coroutine`, `blocking-call-in-async`, `bare-except-too-broad`, `missing-type-hints` to drop off.
- [ ] Two concurrent `await cached_http_get(same_url)` calls produce exactly one outbound HTTP request (verify with `httpx` mock transport or a counter).
- [ ] Cache size stays `<= _CACHE_MAX_ENTRIES` after a flood of distinct URLs.
