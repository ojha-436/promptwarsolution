"""
Auth dependency tests for the real (AUTH_DISABLED=false) path.

`verify_id_token` is mocked so no Firebase network call is made. These tests
cover the 401 paths and the success path, and assert that a rejection never
leaks the underlying verification error to the client.
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException

import app.middleware.auth as auth_mod
from app.config import Settings
from app.middleware.auth import AuthenticatedUser, get_current_user


def _settings(auth_disabled: bool = False) -> Settings:
    return Settings(  # type: ignore[call-arg]
        GCP_PROJECT="t", GEMINI_API_KEY="t", AUTH_DISABLED=auth_disabled
    )


def test_missing_header_is_401():
    with pytest.raises(HTTPException) as exc:
        get_current_user(authorization=None, settings=_settings())
    assert exc.value.status_code == 401
    assert exc.value.detail == "missing bearer token"


def test_non_bearer_scheme_is_401():
    with pytest.raises(HTTPException) as exc:
        get_current_user(authorization="Basic abc123", settings=_settings())
    assert exc.value.status_code == 401


def test_auth_disabled_returns_test_user():
    user = get_current_user(authorization=None, settings=_settings(auth_disabled=True))
    assert isinstance(user, AuthenticatedUser)
    assert user.uid == "test-user"


def test_valid_token_returns_user(monkeypatch):
    monkeypatch.setattr(
        auth_mod.fb_auth,
        "verify_id_token",
        lambda _token, check_revoked=True: {
            "uid": "u-123",
            "email": "traveler@example.com",
            "email_verified": True,
        },
    )
    user = get_current_user(authorization="Bearer valid.jwt.token", settings=_settings())
    assert user.uid == "u-123"
    assert user.email == "traveler@example.com"
    assert user.email_verified is True


def test_invalid_token_returns_generic_message_without_leak(monkeypatch):
    def _raise(_token, check_revoked=True):
        raise ValueError("internal signature mismatch at kid=abc123")

    monkeypatch.setattr(auth_mod.fb_auth, "verify_id_token", _raise)

    with pytest.raises(HTTPException) as exc:
        get_current_user(authorization="Bearer tampered", settings=_settings())

    assert exc.value.status_code == 401
    assert exc.value.detail == "invalid or expired token"
    # The internal reason must never reach the client.
    assert "signature" not in str(exc.value.detail)
    assert "kid=" not in str(exc.value.detail)
