"""
Firebase ID-token verification.

Every request to a protected route MUST carry:
    Authorization: Bearer <firebase id token>

We verify the token with the Firebase Admin SDK on every request — there is
no server-side session, no cookies, no shared secret. This means a stolen
session cookie cannot be used; tokens are short-lived (1h) and revocable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from firebase_admin import auth as fb_auth  # type: ignore[import-untyped]

from app.config import Settings, get_settings


@dataclass(frozen=True)
class AuthenticatedUser:
    uid: str
    email: str | None
    email_verified: bool


def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
    settings: Settings = Depends(get_settings),
) -> AuthenticatedUser:
    """FastAPI dependency. Raises 401 on any auth failure."""
    if settings.AUTH_DISABLED:  # tests only
        return AuthenticatedUser(uid="test-user", email="test@example.com", email_verified=True)

    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing bearer token")

    token = authorization.split(" ", 1)[1].strip()

    try:
        # check_revoked=True hits the auth backend and respects manual revocation.
        decoded = fb_auth.verify_id_token(token, check_revoked=True)
    except (
        fb_auth.RevokedIdTokenError,
        fb_auth.ExpiredIdTokenError,
        fb_auth.InvalidIdTokenError,
        ValueError,
    ) as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"invalid token: {exc}") from exc

    return AuthenticatedUser(
        uid=decoded["uid"],
        email=decoded.get("email"),
        email_verified=bool(decoded.get("email_verified", False)),
    )
