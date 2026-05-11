"""FastAPI login endpoint that verifies credentials against an internal auth service.

Secrets (auth service API key, JWT signing key) are loaded from environment
variables at import time. There is no "production API key" embedded in source —
configure the environment before running locally.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone

import httpx
import jwt
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

AUTH_SERVICE_URL = os.environ.get("AUTH_SERVICE_URL", "https://auth.internal/verify")
AUTH_SERVICE_KEY = os.environ["AUTH_SERVICE_KEY"]
JWT_SIGNING_KEY = os.environ["JWT_SIGNING_KEY"]
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
JWT_ISSUER = os.environ.get("JWT_ISSUER", "doctor-api")
JWT_TTL_SECONDS = int(os.environ.get("JWT_TTL_SECONDS", "3600"))
AUTH_TIMEOUT_SECONDS = float(os.environ.get("AUTH_TIMEOUT_SECONDS", "5.0"))

app = FastAPI(title="doctor-auth")


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=256)
    password: str = Field(min_length=1, max_length=1024)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class VerifiedUser(BaseModel):
    user_id: str
    username: str


async def _verify_with_auth_service(username: str, password: str) -> VerifiedUser:
    """Call the internal auth service and return the verified user.

    Raises HTTPException with a sanitized status on any failure path. The
    upstream service's response body is never forwarded to the caller.
    """
    payload = {"username": username, "password": password}
    headers = {"Authorization": f"Bearer {AUTH_SERVICE_KEY}"}

    try:
        async with httpx.AsyncClient(timeout=AUTH_TIMEOUT_SECONDS) as client:
            response = await client.post(AUTH_SERVICE_URL, json=payload, headers=headers)
    except httpx.TimeoutException as exc:
        logger.warning("auth service timeout: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="auth service timed out",
        ) from exc
    except httpx.RequestError as exc:
        logger.warning("auth service unreachable: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="auth service unreachable",
        ) from exc

    if response.status_code == status.HTTP_401_UNAUTHORIZED:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid credentials",
        )
    if response.status_code >= 500:
        logger.warning("auth service 5xx: status=%s", response.status_code)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="auth service error",
        )
    if response.status_code != status.HTTP_200_OK:
        logger.warning("auth service unexpected status: %s", response.status_code)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="auth service error",
        )

    try:
        body = response.json()
    except ValueError as exc:
        logger.warning("auth service returned non-JSON body: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="auth service error",
        ) from exc

    if not isinstance(body, dict):
        logger.warning("auth service returned non-object body: type=%s", type(body).__name__)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="auth service error",
        )

    user_id = body.get("user_id")
    verified_username = body.get("username", username)
    if not isinstance(user_id, str) or not isinstance(verified_username, str):
        logger.warning("auth service response missing required fields")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="auth service error",
        )

    return VerifiedUser(user_id=user_id, username=verified_username)


def _issue_jwt(user: VerifiedUser) -> tuple[str, int]:
    """Sign a JWT for the verified user. Returns (token, expires_in_seconds)."""
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=JWT_TTL_SECONDS)
    claims = {
        "sub": user.user_id,
        "preferred_username": user.username,
        "iss": JWT_ISSUER,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    token = jwt.encode(claims, JWT_SIGNING_KEY, algorithm=JWT_ALGORITHM)
    return token, JWT_TTL_SECONDS


@app.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest) -> LoginResponse:
    user = await _verify_with_auth_service(payload.username, payload.password)
    token, expires_in = _issue_jwt(user)
    return LoginResponse(access_token=token, expires_in=expires_in)
