import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import bcrypt
from jose import JWTError, jwt

from app.core.config import get_settings

settings = get_settings()

TokenType = Literal["access", "refresh"]


class InvalidTokenError(Exception):
    """Raised when a token is missing, expired, malformed, or the wrong type."""


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def _create_token(subject: str, expires_delta: timedelta, token_type: TokenType) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
        "jti": str(uuid.uuid4()),
    }
    token: str = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token


def create_access_token(subject: str) -> str:
    expires_delta = timedelta(minutes=settings.access_token_expire_minutes)
    return _create_token(subject, expires_delta, "access")


def create_refresh_token(subject: str) -> str:
    expires_delta = timedelta(days=settings.refresh_token_expire_days)
    return _create_token(subject, expires_delta, "refresh")


def decode_token(token: str, expected_type: TokenType) -> dict[str, Any]:
    """Decode and validate a JWT. Raises InvalidTokenError for any failure mode
    (expired, malformed, wrong signature, wrong token type) so callers don't need
    to know about jose's exception hierarchy.
    """
    try:
        payload: dict[str, Any] = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
    except JWTError as exc:
        raise InvalidTokenError("Token is invalid or expired") from exc

    if payload.get("type") != expected_type:
        raise InvalidTokenError(f"Expected a {expected_type} token")

    return payload
