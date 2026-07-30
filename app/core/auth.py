"""JWT authentication + role-based access control.

Issues signed JWTs (HS256), verifies them, and exposes helpers for
role-based checks. Credentials are validated against a small demo user
store — in production this would be a database with hashed passwords; the
token-issue/verify machinery here is the real, reusable part.
"""
from __future__ import annotations

import time

import jwt

from app.core.config import get_settings

ALGORITHM = "HS256"
DEFAULT_TTL_SECONDS = 3600

# Demo credentials. Replace with a real user table + password hashing.
_DEMO_USERS: dict[str, tuple[str, str]] = {
    # username: (password, role)
    "admin": ("admin123", "admin"),
    "user": ("user123", "user"),
}


class AuthError(Exception):
    """Raised for invalid credentials or tokens."""


def _secret() -> str:
    return get_settings().jwt_secret or "dev-secret-change-me"


def verify_credentials(username: str, password: str) -> str | None:
    """Return the user's role if credentials are valid, else None."""
    record = _DEMO_USERS.get(username)
    if record and record[0] == password:
        return record[1]
    return None


def create_access_token(
    subject: str, role: str = "user", expires_in: int = DEFAULT_TTL_SECONDS
) -> str:
    """Create a signed JWT for `subject` with a role and expiry."""
    now = int(time.time())
    payload = {"sub": subject, "role": role, "iat": now, "exp": now + expires_in}
    return jwt.encode(payload, _secret(), algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode + verify a JWT. Raises AuthError on expiry/invalidity."""
    try:
        return jwt.decode(token, _secret(), algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise AuthError("token expired") from exc
    except jwt.PyJWTError as exc:
        raise AuthError("invalid token") from exc
