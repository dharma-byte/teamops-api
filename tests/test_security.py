from datetime import UTC, datetime, timedelta

import pytest
from jose import jwt

from app.core.config import get_settings
from app.core.security import (
    InvalidTokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)

settings = get_settings()


def test_hash_password_verifies_correctly() -> None:
    hashed = hash_password("correct horse battery staple")

    assert hashed != "correct horse battery staple"
    assert verify_password("correct horse battery staple", hashed)
    assert not verify_password("wrong password", hashed)


def test_access_token_round_trips_subject() -> None:
    token = create_access_token(subject="user-123")

    payload = decode_token(token, expected_type="access")

    assert payload["sub"] == "user-123"
    assert payload["type"] == "access"


def test_refresh_token_round_trips_subject() -> None:
    token = create_refresh_token(subject="user-123")

    payload = decode_token(token, expected_type="refresh")

    assert payload["sub"] == "user-123"
    assert payload["type"] == "refresh"


def test_decode_rejects_wrong_token_type() -> None:
    access_token = create_access_token(subject="user-123")

    with pytest.raises(InvalidTokenError):
        decode_token(access_token, expected_type="refresh")


def test_decode_rejects_expired_token() -> None:
    expired_payload = {
        "sub": "user-123",
        "type": "access",
        "iat": datetime.now(UTC) - timedelta(minutes=20),
        "exp": datetime.now(UTC) - timedelta(minutes=5),
    }
    expired_token = jwt.encode(
        expired_payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )

    with pytest.raises(InvalidTokenError):
        decode_token(expired_token, expected_type="access")


def test_decode_rejects_tampered_signature() -> None:
    token = create_access_token(subject="user-123")

    with pytest.raises(InvalidTokenError):
        decode_token(token + "tampered", expected_type="access")
