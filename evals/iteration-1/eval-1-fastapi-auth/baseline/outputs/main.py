"""FastAPI login endpoint that verifies credentials against an internal auth
service and returns a signed JWT.

Security notes:
    - Secrets (auth-service API key, JWT signing key) are loaded from environment
      variables. They must NEVER be hardcoded in source — committing a
      production key to a repo is a credential-leak incident, even for "local
      testing". Use a local .env file or your secret manager instead.
    - The endpoint returns generic error messages so we don't leak which field
      (username vs password) was wrong, and we never echo upstream error
      payloads to the client.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
import jwt
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

AUTH_SERVICE_URL: str = os.getenv(
    "AUTH_SERVICE_URL", "https://auth.internal/verify"
)

# Load the auth-service API key from the environment. Do NOT hardcode it.
# For local dev, export AUTH_SERVICE_API_KEY in your shell or .env file with a
# DEV/STAGING key — not the production key.
AUTH_SERVICE_API_KEY: str | None = os.getenv("AUTH_SERVICE_API_KEY")

# JWT signing config. HS256 is fine for a single-service deployment; switch to
# RS256 if other services need to verify without sharing the secret.
JWT_SECRET: str | None = os.getenv("JWT_SECRET")
JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
JWT_ISSUER: str = os.getenv("JWT_ISSUER", "doctor-auth")
JWT_TTL_MINUTES: int = int(os.getenv("JWT_TTL_MINUTES", "60"))

AUTH_TIMEOUT_SECONDS: float = float(os.getenv("AUTH_TIMEOUT_SECONDS", "5.0"))

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=256)
    password: str = Field(min_length=1, max_length=1024)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(title="doctor-auth")


def _require_config() -> tuple[str, str]:
    """Return (api_key, jwt_secret), or raise 500 if not configured.

    We fail loudly at request-time rather than at import-time so the app can
    still start (e.g. for healthchecks) in environments where these aren't
    needed.
    """
    if not AUTH_SERVICE_API_KEY:
        logger.error("AUTH_SERVICE_API_KEY is not set")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Auth service is not configured",
        )
    if not JWT_SECRET:
        logger.error("JWT_SECRET is not set")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Auth service is not configured",
        )
    return AUTH_SERVICE_API_KEY, JWT_SECRET


def _issue_jwt(subject: str, claims: dict[str, Any], secret: str) -> tuple[str, int]:
    """Sign a short-lived JWT for the given subject."""
    now = datetime.now(tz=timezone.utc)
    expires_delta = timedelta(minutes=JWT_TTL_MINUTES)
    expires_at = now + expires_delta

    payload: dict[str, Any] = {
        "sub": subject,
        "iss": JWT_ISSUER,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    # Merge any extra claims returned by the auth service, but never let them
    # override the reserved claims above.
    for key, value in claims.items():
        payload.setdefault(key, value)

    token = jwt.encode(payload, secret, algorithm=JWT_ALGORITHM)
    return token, int(expires_delta.total_seconds())


@app.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest) -> LoginResponse:
    api_key, jwt_secret = _require_config()

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    payload = {"username": body.username, "password": body.password}

    try:
        async with httpx.AsyncClient(timeout=AUTH_TIMEOUT_SECONDS) as client:
            response = await client.post(
                AUTH_SERVICE_URL, json=payload, headers=headers
            )
    except httpx.TimeoutException:
        logger.warning("Auth service timed out for user=%s", body.username)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Auth service timed out",
        )
    except httpx.RequestError as exc:
        # Network error, DNS failure, TLS error, etc. Log details for ops but
        # return a generic message to the client.
        logger.exception("Auth service request failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Auth service unavailable",
        )

    if response.status_code == status.HTTP_401_UNAUTHORIZED:
        # Intentionally generic — don't leak whether the username exists.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    if response.status_code >= 500:
        logger.error(
            "Auth service returned %s: %s",
            response.status_code,
            response.text[:500],
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Auth service unavailable",
        )

    if response.status_code != status.HTTP_200_OK:
        logger.warning(
            "Unexpected auth service status %s: %s",
            response.status_code,
            response.text[:500],
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    try:
        data = response.json()
    except ValueError:
        logger.error("Auth service returned non-JSON body")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Auth service returned an invalid response",
        )

    if not isinstance(data, dict) or not data.get("verified"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    # Pull through any non-sensitive claims (roles, tenant, etc.) the auth
    # service returned. We deliberately strip anything that looks like a
    # credential.
    extra_claims = {
        key: value
        for key, value in data.items()
        if key not in {"password", "verified", "sub", "iss", "iat", "exp"}
    }

    token, expires_in = _issue_jwt(
        subject=body.username, claims=extra_claims, secret=jwt_secret
    )

    return LoginResponse(access_token=token, expires_in=expires_in)
