# /aidoctor:simplify — eval-1 fastapi-auth baseline review

## Phase 1 — Identified changes

The entire file `evals/iteration-1/eval-1-fastapi-auth/baseline/outputs/main.py` (~205 lines) is under review. It implements a FastAPI `/login` endpoint that:

1. Loads config (auth-service URL, API key, JWT signing key, algorithm, issuer, TTL, timeout) from environment variables at import time.
2. Defines Pydantic `LoginRequest` / `LoginResponse` models.
3. Exposes a single `POST /login` route that:
   - Validates required config (`_require_config`) at request time.
   - Posts credentials to an upstream `AUTH_SERVICE_URL` via `httpx.AsyncClient`.
   - Distinguishes timeout / network error / 401 / 5xx / unexpected-status / non-JSON / `verified=False` cases, returning generic 401/502/504 messages.
   - Strips reserved JWT claims out of any extra fields returned by the auth service.
   - Issues a short-lived HS256 JWT via `_issue_jwt` and returns `LoginResponse`.

Key surface area for the review:
- Lines 26–27: `logging.basicConfig(level=logging.INFO)` at module import.
- Lines 33–49: env-var config block.
- Lines 74–93: `_require_config` (duplicated branches for two missing-config checks).
- Lines 96–114: `_issue_jwt` (returns `(token, expires_in)`; reserved-claim handling).
- Lines 117–205: `login` endpoint (long linear function; per-request `AsyncClient`; multiple `HTTPException` raises with similar shapes; `raise` from `except` blocks without `from`).

## Phase 2 — Three-angle findings

### Reviewer 1: Code Reuse

- **Lines 81–92 — Duplicate config-missing branches in `_require_config`.** Two near-identical `if not X: logger.error(...); raise HTTPException(500, "Auth service is not configured")` blocks. Could be a single loop over a `[("AUTH_SERVICE_API_KEY", AUTH_SERVICE_API_KEY), ("JWT_SECRET", JWT_SECRET)]` list, or a tiny helper `_require(name, value)`.
- **Lines 148–153, 166–175, 186–190 — Three "Invalid username or password" `HTTPException(401)` raises** with identical shape. A `_invalid_credentials()` helper (or a module-level pre-built `HTTPException`) would consolidate them.
- **Lines 143–146 and 161–164 — Two "Auth service unavailable" 502 raises** with identical body. Same consolidation opportunity (`_upstream_unavailable()` helper or constant).
- **Lines 156–160 and 167–171 — Two `logger.<level>("... %s: %s", response.status_code, response.text[:500])` calls** that differ only by log level. A `_log_upstream(level, response)` helper would dedupe; the `[:500]` truncation magic number is also repeated.
- **Lines 117–205 — No reuse of `httpx.AsyncClient`.** A new client is constructed per request. Standard FastAPI pattern is one module-level `AsyncClient` (or a dependency) reused across requests — this is both a reuse and an efficiency finding.
- **Line 26–27 — `logging.basicConfig` at import time** duplicates what FastAPI/uvicorn already configure. Reuse the existing logger config rather than forcing a global re-init.

### Reviewer 2: Code Quality

- **Lines 33–49 — Module-level env reads** make the module hard to test (you have to monkeypatch globals or reload the module). A small `Settings` dataclass / Pydantic `BaseSettings` read once via a cached function (`@lru_cache`) is the standard pattern and removes the global-mutability smell.
- **Lines 74–93 — `_require_config` re-reads module globals every call**, so it can't be safely re-used in tests that override env. Same Settings fix applies; the function then becomes a one-liner property access.
- **Lines 135–138, 143–146, 161–164, 172–175, 181–184, 187–190 — `raise HTTPException(...)` inside `except` blocks without `from exc` / `from None`.** Python best practice (and an aidoctor-flavored rule) is to chain or explicitly suppress: `raise HTTPException(...) from exc`. As written, the original exception context is preserved implicitly but the linter will (rightly) complain.
- **Lines 96–114 — `_issue_jwt` returns a `tuple[str, int]`** where the `int` is just `JWT_TTL_MINUTES * 60`. The caller already knows the TTL config; returning it as part of the tuple is parameter-sprawl-via-return-value. Either return just the token and compute `expires_in` once at module level, or return a small `IssuedToken` dataclass.
- **Lines 110–111 — `payload.setdefault(key, value)` loop** is a hand-rolled "don't override reserved claims" guard. Cleaner: `payload = {**extra_claims, **reserved}` (reserved wins) — one expression, no loop, intent obvious.
- **Lines 192–199 — Hand-rolled "strip sensitive keys" dict comprehension** with an inline literal set. The set of reserved/forbidden claim names is duplicated knowledge with `_issue_jwt`'s reserved-claim list (lines 102–107). Define `_RESERVED_CLAIMS = frozenset({...})` once and reuse.
- **Lines 1–12 — Module docstring carries a long "Security notes" prose section** that narrates rather than documents API. Useful for a README; noisy at the top of a code file. Trim to one sentence ("Loads secrets from env; never hardcode.") or move to `SECURITY.md`.
- **Lines 37–39, 42–43, 108–109, 140–142, 148–149, 192–194 — Inline narration comments** ("Do NOT hardcode it", "HS256 is fine…", "Merge any extra claims…", "Network error, DNS failure…", "Intentionally generic…", "Pull through any non-sensitive claims…") explain WHAT the next line does. Most of these can be deleted; keep only the "Intentionally generic — don't leak whether the username exists" comment since it documents a non-obvious WHY (security decision).
- **Lines 26–27 — `logging.basicConfig(level=logging.INFO)` at import** is a side effect at import time; aidoctor-style rule violation (modules shouldn't reconfigure global logging on import). Move to an explicit `configure_logging()` called from app startup, or rely on the ASGI server's logger.
- **Line 47 — `int(os.getenv("JWT_TTL_MINUTES", "60"))`** silently crashes at import if someone sets `JWT_TTL_MINUTES=foo`. A Pydantic `BaseSettings` would give a clean validation error.

### Reviewer 3: Efficiency

- **Lines 129–132 — `async with httpx.AsyncClient(...)` constructed per request.** Each call opens a fresh connection pool and TLS handshake. Standard fix: one module-level `AsyncClient` instantiated at app startup (`@app.on_event("startup")` or lifespan), reused across requests, closed at shutdown. This is the single biggest perf win — auth endpoints are hot paths and TLS-handshake-per-login is wasteful.
- **Line 27 — `logging.basicConfig` at import time** is hot-path bloat at module load (cheap, but unnecessary), and worse, it competes with uvicorn's own logger setup.
- **Lines 158–159, 169–170 — `response.text[:500]` reads the entire body into a Python string** before truncating. For a 50MB hostile/erroneous upstream body this is wasteful. Use `response.text[:500]` only after checking `len(response.content) < some_limit`, or set `httpx`'s `max_response_size` / read with `response.aread()` capped — minor, but worth noting.
- **Lines 99–101 — `datetime.now(tz=timezone.utc)` + `timedelta` + two `.timestamp()` casts** per issuance. Fine, but if you precompute `JWT_TTL_SECONDS = JWT_TTL_MINUTES * 60` once at module level, you save the `int(expires_delta.total_seconds())` call and one `timedelta` allocation per login. Micro-optimization; flagging for completeness.
- **Lines 195–199 — Dict comprehension iterating `data.items()`** with a per-key set membership check is O(n) and fine for small claim sets, but the set literal `{"password", "verified", ...}` is reconstructed on every login. Hoist to a module-level `frozenset` constant (also dedups with `_issue_jwt`).
- **Lines 117–205 — No upstream-error rate limiting / circuit breaker.** Not strictly an "efficiency" finding for a single request, but if the auth service goes down, every login attempt waits the full 5s timeout. Out of scope for a simplify pass; flagged as future work.

## Phase 3 — Decision brief (what would you propose to fix?)

```
D1 — Which findings should I fix?
ELI10: The three reviewers flagged ~14 unique issues. The big wins are
(1) reuse one httpx.AsyncClient instead of building one per request — real perf,
(2) collapse the duplicate config / HTTPException / log blocks into helpers — readability,
(3) add `from exc` to re-raises inside except blocks — correctness/linter,
(4) hoist the reserved-claims set so `_issue_jwt` and the login handler share one source of truth — quality.
The rest (docstring trimming, comment pruning, BaseSettings migration) are taste calls.

Recommendation: A because the consensus findings (client reuse, dedup helpers,
`from exc`, shared reserved-claims set) are flagged by 2+ reviewers and are the
highest-confidence wins.

A) Fix only findings flagged by 2+ reviewers (recommended)
  - Module-level httpx.AsyncClient via lifespan (Reuse + Efficiency)
  - `_invalid_credentials()` / `_upstream_unavailable()` helpers (Reuse + Quality)
  - `raise ... from exc` on the three except blocks (Quality)
  - `_RESERVED_CLAIMS` frozenset shared by `_issue_jwt` and login (Reuse + Quality + Efficiency)
  - Collapse `_require_config` duplicate branches (Reuse + Quality)
  ✅ Highest signal-to-noise; targeted ~30-line diff; measurable perf win
  ❌ Skips BaseSettings migration and docstring trim

B) Fix all ~14 unique findings
  ✅ Cleanest end state; addresses comments + BaseSettings + JWT_TTL_SECONDS hoist
  ❌ Bigger diff; BaseSettings migration touches every config consumer; some
     comment removals are taste calls

C) Show me the list, I'll pick
  ✅ Full control
  ❌ Slower

Net: A is the right default. The file is already reasonable; the wins are
focused on the per-request httpx client and the duplicate-block dedup.
```

## Phase 4 — If user accepts your recommendation

Concrete edits I would apply (option A):

1. **Add module-level reserved-claims constant** (new lines after line 49):
   ```python
   _RESERVED_CLAIMS: frozenset[str] = frozenset(
       {"sub", "iss", "iat", "exp", "password", "verified"}
   )
   _JWT_TTL_SECONDS: int = JWT_TTL_MINUTES * 60
   ```

2. **Add module-level shared HTTPException factories** (new lines after the constants above):
   ```python
   def _invalid_credentials() -> HTTPException:
       return HTTPException(
           status_code=status.HTTP_401_UNAUTHORIZED,
           detail="Invalid username or password",
       )

   def _upstream_unavailable() -> HTTPException:
       return HTTPException(
           status_code=status.HTTP_502_BAD_GATEWAY,
           detail="Auth service unavailable",
       )
   ```

3. **Collapse `_require_config` duplicate branches** (replace lines 74–93):
   ```python
   def _require_config() -> tuple[str, str]:
       required = {"AUTH_SERVICE_API_KEY": AUTH_SERVICE_API_KEY, "JWT_SECRET": JWT_SECRET}
       missing = [name for name, value in required.items() if not value]
       if missing:
           logger.error("Missing required config: %s", ", ".join(missing))
           raise HTTPException(
               status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
               detail="Auth service is not configured",
           )
       return AUTH_SERVICE_API_KEY, JWT_SECRET  # type: ignore[return-value]
   ```

4. **Simplify `_issue_jwt` reserved-claim handling and reuse `_JWT_TTL_SECONDS`** (replace lines 96–114):
   ```python
   def _issue_jwt(subject: str, claims: dict[str, Any], secret: str) -> tuple[str, int]:
       """Sign a short-lived JWT for the given subject."""
       now = datetime.now(tz=timezone.utc)
       reserved = {
           "sub": subject,
           "iss": JWT_ISSUER,
           "iat": int(now.timestamp()),
           "exp": int((now + timedelta(seconds=_JWT_TTL_SECONDS)).timestamp()),
       }
       payload: dict[str, Any] = {**claims, **reserved}  # reserved wins
       token = jwt.encode(payload, secret, algorithm=JWT_ALGORITHM)
       return token, _JWT_TTL_SECONDS
   ```

5. **Introduce a lifespan-managed shared `httpx.AsyncClient`** (replace `app = FastAPI(...)` on line 71 and per-request client at lines 129–132):
   ```python
   from contextlib import asynccontextmanager

   @asynccontextmanager
   async def lifespan(app: FastAPI):
       app.state.http = httpx.AsyncClient(timeout=AUTH_TIMEOUT_SECONDS)
       try:
           yield
       finally:
           await app.state.http.aclose()

   app = FastAPI(title="doctor-auth", lifespan=lifespan)
   ```
   And in `login`, replace the `async with httpx.AsyncClient(...)` block with:
   ```python
   try:
       response = await app.state.http.post(
           AUTH_SERVICE_URL, json=payload, headers=headers
       )
   except httpx.TimeoutException as exc:
       ...
   ```

6. **Add `from exc` to re-raises** (lines 135–138, 143–146, 181–184):
   ```python
   except httpx.TimeoutException as exc:
       logger.warning("Auth service timed out for user=%s", body.username)
       raise HTTPException(
           status_code=status.HTTP_504_GATEWAY_TIMEOUT,
           detail="Auth service timed out",
       ) from exc
   except httpx.RequestError as exc:
       logger.exception("Auth service request failed: %s", exc)
       raise _upstream_unavailable() from exc
   ```
   And in the JSON decode branch (lines 177–184):
   ```python
   try:
       data = response.json()
   except ValueError as exc:
       logger.error("Auth service returned non-JSON body")
       raise HTTPException(
           status_code=status.HTTP_502_BAD_GATEWAY,
           detail="Auth service returned an invalid response",
       ) from exc
   ```

7. **Replace duplicate raise sites with helpers** (lines 148–153, 161–164, 172–175, 186–190):
   ```python
   if response.status_code == status.HTTP_401_UNAUTHORIZED:
       raise _invalid_credentials()
   if response.status_code >= 500:
       logger.error("Auth service returned %s: %s", response.status_code, response.text[:500])
       raise _upstream_unavailable()
   if response.status_code != status.HTTP_200_OK:
       logger.warning("Unexpected auth service status %s: %s", response.status_code, response.text[:500])
       raise _invalid_credentials()
   ...
   if not isinstance(data, dict) or not data.get("verified"):
       raise _invalid_credentials()
   ```

8. **Use shared `_RESERVED_CLAIMS` in the extra-claims filter** (replace lines 195–199):
   ```python
   extra_claims = {k: v for k, v in data.items() if k not in _RESERVED_CLAIMS}
   ```

9. **Remove `logging.basicConfig(level=logging.INFO)`** at line 27. Let the ASGI server (uvicorn) configure logging; the module just gets its logger.

Net diff: ~50 lines touched, ~15 lines net removed, one measurable perf win (shared AsyncClient), and three duplicate code patterns collapsed to single sources of truth.
